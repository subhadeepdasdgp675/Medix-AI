import sqlite3
import os
import time
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medix_auth.db")

def init_auth_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            full_name TEXT,
            role TEXT,
            reg_number TEXT,
            verified INTEGER DEFAULT 1,
            created_at REAL
        )
    """)
    conn.commit()
    conn.close()

def create_or_update_user(email: str, password: str, full_name: Optional[str] = "", role: Optional[str] = "doctor", reg_number: Optional[str] = "") -> bool:
    init_auth_db()
    email_clean = email.strip().lower()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO users (email, password, full_name, role, reg_number, verified, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        """, (email_clean, password, full_name or "", role or "doctor", reg_number or "", time.time()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[AuthDB Error] Failed to create user {email}: {e}")
        return False

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    init_auth_db()
    email_clean = email.strip().lower()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT email, password, full_name, role, reg_number, verified FROM users WHERE email = ?", (email_clean,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        stored_email, stored_pass, full_name, role, reg_number, verified = row
        if stored_pass == password and verified == 1:
            return {
                "id": f"medix-usr-{abs(hash(stored_email)) % 1000000}",
                "email": stored_email,
                "full_name": full_name,
                "role": role,
                "reg_number": reg_number
            }
        return None
    except Exception as e:
        print(f"[AuthDB Error] Failed to authenticate user {email}: {e}")
        return None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    init_auth_db()
    email_clean = email.strip().lower()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT email, full_name, role, reg_number, verified FROM users WHERE email = ?", (email_clean,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        stored_email, full_name, role, reg_number, verified = row
        return {
            "email": stored_email,
            "full_name": full_name,
            "role": role,
            "reg_number": reg_number,
            "verified": bool(verified)
        }
    except Exception as e:
        return None
