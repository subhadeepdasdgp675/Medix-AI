import os
import time
import random
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Tuple, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

# In-memory storage for active OTP codes
# Key: normalized email (lowercase, stripped), Value: Dict with otp, expires_at, verified, etc.
OTP_STORE: Dict[str, Dict[str, Any]] = {}

# Comprehensive list of known disposable/temporary/arbitrary email domains
DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "yopmail.com", "getairmail.com", "sharklasers.com", "dispostable.com",
    "trashmail.com", "temp-mail.org", "fakeinbox.com", "maildrop.cc",
    "inopisty.com", "mailg.cf", "mohmal.com", "crazymailing.com",
    "throwawaymail.com", "mailnesia.com", "yandex.net", "klzlk.com",
    "getnada.com", "burnermail.io", "spambox.us", "jetable.org",
    "emailfake.com", "mailcatch.com", "tempinbox.com", "anonymbox.com"
}

def check_arbitrary_email_heuristics(email: str, full_name: Optional[str] = None, role: Optional[str] = "doctor") -> Tuple[bool, str]:
    """
    Rule-based check against arbitrary/disposable emails and gibberish patterns.
    """
    if not email or "@" not in email:
        return False, "Invalid email address format."
    
    email_clean = email.strip().lower()
    local_part, domain = email_clean.split("@", 1)
    
    # 1. Check against disposable/temporary domains
    if domain in DISPOSABLE_DOMAINS:
        return False, f"Disposable or temporary email domain ('{domain}') is not allowed for healthcare provider registration."
    
    # 2. Check for obvious gibberish or keyboard mashing in local_part
    gibberish_patterns = [
        r"^[a-z]{1,2}\d{5,}\$", # e.g. a123456@
        r"^(asdf|qwerty|zxcv|test|dummy|fake|spam|random|arbitrary)",
        r"^[0-9]{6,}@", # pure numbers like 12345678@
    ]
    for pat in gibberish_patterns:
        if re.search(pat, local_part):
            return False, "Email address appears to be arbitrary or placeholder text. Please enter your valid institutional or professional medical email."
            
    # 3. Check domain validity
    if "." not in domain or len(domain.split(".")[-1]) < 2:
        return False, "Invalid top-level domain in email address."
        
    return True, "Heuristic validation passed."

async def check_email_validity_with_ai(email: str, full_name: Optional[str] = None, role: Optional[str] = "doctor", reg_number: Optional[str] = None) -> Tuple[bool, str]:
    """
    Evaluates registration credentials using Google Gemini API to strictly enforce:
    'No arbitrary email should be signed up.'
    Falls back to heuristics if Gemini API key is not configured or unreachable.
    """
    # Run local heuristic check first
    passed, reason = check_arbitrary_email_heuristics(email, full_name, role)
    if not passed:
        return False, reason
        
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return True, "Heuristic validation passed (Gemini API key not configured)."
        
    try:
        prompt = f"""You are the clinical security and identity verification AI for Medix AI, an enterprise-grade medical AI platform designed exclusively for verified Doctors and Hospitals.
We must strictly enforce our policy: "No arbitrary email should be signed up."

Evaluate the following registration attempt:
Role: {role}
Name/Institution: {full_name or 'Not provided'}
Registration/Hospital ID: {reg_number or 'Not provided'}
Email Address: {email}

Please analyze the email address and credentials:
1. Is the email address from a temporary/disposable/trash service or clearly arbitrary/gibberish/fake?
2. Does the registration information appear plausible and legitimate for a healthcare provider (Doctor or Hospital)?
Note: Standard reputable email providers like gmail.com, outlook.com, yahoo.com, or hospital/academic domains (.org, .edu, .gov, hospital domains) are completely ACCEPTABLE as long as the username part looks genuine rather than random keyboard mashing (e.g. 'asdfgh123@gmail.com' is arbitrary and should be rejected, whereas 'dr.rohit.sharma@gmail.com' or 'general.hospital.admin@gmail.com' is legitimate and should be accepted).

Respond strictly with a JSON object containing exactly two keys:
{{
  "is_valid": true or false,
  "reason": "Clear explanation of why this registration is accepted or why it is rejected as arbitrary/suspicious"
}}
Return only valid JSON without markdown formatting or code blocks if possible.
"""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                # Clean up any potential code block formatting
                cleaned_text = re.sub(r"^```json\s*", "", text.strip())
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
                result = json.loads(cleaned_text)
                
                is_valid = bool(result.get("is_valid", True))
                ai_reason = result.get("reason", "AI verification completed.")
                if not is_valid:
                    return False, f"AI Security Check Failed: {ai_reason}"
                return True, ai_reason
            else:
                # Fallback to model 1.5 if 2.5 is not available or errors out
                url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                resp_fb = await client.post(url_fallback, json=payload)
                if resp_fb.status_code == 200:
                    data = resp_fb.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    cleaned_text = re.sub(r"^```json\s*", "", text.strip())
                    cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
                    result = json.loads(cleaned_text)
                    is_valid = bool(result.get("is_valid", True))
                    ai_reason = result.get("reason", "AI verification completed.")
                    if not is_valid:
                        return False, f"AI Security Check Failed: {ai_reason}"
                    return True, ai_reason
    except Exception as e:
        print(f"[Notice] Gemini API evaluation fallback due to: {e}")
        
    return True, "Heuristic validation passed."

def send_real_smtp_email(to_email: str, otp_code: str, full_name: Optional[str] = None, role: str = "doctor") -> bool:
    """
    Send OTP code via SMTP if configured in environment variables.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD", "").replace(" ", "")
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user or "noreply@medixai.org")
    
    if not smtp_server or not smtp_user or not smtp_pass:
        return False
        
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Medix AI Verification Code: {otp_code}"
        msg["From"] = from_email
        msg["To"] = to_email
        
        name_display = full_name or ("Doctor" if role == "doctor" else "Hospital Administrator")
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0b0f19; color: #e1e7ef; padding: 30px;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #131b2e; border: 1px solid #233050; border-radius: 12px; padding: 30px; text-align: center;">
                <h2 style="color: #00d9ff; margin-bottom: 20px;">MEDIX AI</h2>
                <h3 style="color: #ffffff; margin-top: 0;">Verify Your Email Address</h3>
                <p style="color: #a0aec0; font-size: 15px;">Hello {name_display},</p>
                <p style="color: #a0aec0; font-size: 15px;">Please use the following 6-digit verification code to complete your secure Medix AI registration:</p>
                
                <div style="background-color: #1a253f; border: 2px solid #00d9ff; border-radius: 8px; padding: 15px 25px; font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #00d9ff; margin: 25px 0;">
                    {otp_code}
                </div>
                
                <p style="color: #718096; font-size: 13px;">This code will expire in 10 minutes. If you did not request this verification, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #233050; margin: 25px 0;" />
                <p style="color: #4a5568; font-size: 12px;">© 2026 Medix AI — Enterprise Clinical Intelligence</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))
        
        print(f"[MEDIX AI AUTH — SMTP DISPATCH] Sending verification code from <{from_email}> to <{to_email}>...")
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [to_email], msg.as_string())
        print(f"[MEDIX AI AUTH — SMTP DISPATCH] SUCCESS! Envelope delivered directly to <{to_email}>.")
        return True
    except Exception as e:
        print(f"[Notice] SMTP send failed: {e}")
        return False

async def generate_and_send_otp(email: str, full_name: Optional[str] = None, role: Optional[str] = "doctor", reg_number: Optional[str] = None) -> Dict[str, Any]:
    """
    Validates email/credentials, generates a 6-digit OTP, stores it, and delivers via real SMTP.
    """
    email_clean = email.strip().lower()
    
    # Check arbitrary email policy with heuristics + Gemini AI
    is_valid, reason = await check_email_validity_with_ai(email_clean, full_name, role, reg_number)
    if not is_valid:
        return {
            "status": "error",
            "detail": reason
        }
        
    # Generate 6-digit OTP code
    otp_code = f"{random.randint(100000, 999999)}"
    expires_at = time.time() + 600  # 10 minutes expiry
    
    OTP_STORE[email_clean] = {
        "otp": otp_code,
        "expires_at": expires_at,
        "role": role,
        "full_name": full_name,
        "reg_number": reg_number,
        "verified": False
    }
    
    # Try sending via real SMTP
    smtp_sent = send_real_smtp_email(email_clean, otp_code, full_name, role)
    
    if smtp_sent:
        print(f"[MEDIX AI AUTH] OTP successfully sent to {email_clean} via SMTP.")
        return {
            "status": "success",
            "message": f"Verification code sent to {email_clean}. Please check your inbox and spam folder."
        }
    else:
        banner = f"""
===================================================================
[MEDIX AI AUTH — SERVER LOGGING ONLY]
Verification Code for : {email_clean}
Role                  : {role}
Name                  : {full_name or 'N/A'}
ID/Reg Number         : {reg_number or 'N/A'}
-------------------------------------------------------------------
Your 6-Digit OTP Code : {otp_code}
===================================================================
NOTE: Real SMTP email delivery failed or is not configured in .env.
===================================================================
"""
        print(banner)
        if not os.getenv("SMTP_SERVER") or not os.getenv("SMTP_USERNAME") or not os.getenv("SMTP_PASSWORD"):
            return {
                "status": "error",
                "detail": "Real email delivery requires configuring SMTP settings (SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD) in your .env file."
            }
        return {
            "status": "error",
            "detail": "Failed to deliver email verification code via SMTP. Please check your email and app password in .env."
        }

def verify_otp_code(email: str, otp_code: str) -> Tuple[bool, str]:
    """
    Verifies that the OTP code matches the stored unexpired code for the given email.
    """
    email_clean = email.strip().lower()
    if email_clean not in OTP_STORE:
        return False, "No active verification code found for this email. Please click 'Resend Code'."
        
    record = OTP_STORE[email_clean]
    if time.time() > record["expires_at"]:
        del OTP_STORE[email_clean]
        return False, "Verification code has expired. Please request a new code."
        
    if record["otp"] != otp_code.strip():
        return False, "Incorrect verification code. Please check your digits and try again."
        
    # Mark verified and clean up
    record["verified"] = True
    # We remove the OTP record right after successful verification to prevent reuse
    del OTP_STORE[email_clean]
    return True, "Email verified successfully."
