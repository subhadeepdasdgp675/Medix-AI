<div align="center">
  <img src="src/assets/logo.png" alt="Medix AI Logo" width="120" />
  <h1>Medix AI</h1>
  <p><strong>Next-Generation Antimicrobial Decision-Support Platform</strong></p>

  <p>
    <a href="https://reactjs.org/"><img src="https://img.shields.io/badge/React-19-blue?style=for-the-badge&logo=react" alt="React" /></a>
    <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" /></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python" alt="Python" /></a>
    <a href="https://supabase.com/"><img src="https://img.shields.io/badge/Supabase-Database-3ECF8E?style=for-the-badge&logo=supabase" alt="Supabase" /></a>
    <a href="https://vercel.com/"><img src="https://img.shields.io/badge/Vercel-Deploy-000000?style=for-the-badge&logo=vercel" alt="Vercel" /></a>
  </p>
</div>

---

## 🔬 Overview

**Medix AI** is a state-of-the-art clinical intelligence platform designed to assist healthcare professionals in fighting Antimicrobial Resistance (AMR). By blending machine learning inference, real-time geospatial surveillance, and comprehensive FDA data integration, Medix AI delivers an unparalleled decision-support system right to the physician's dashboard.

Designed with a stunning **glassmorphism** interface, Medix AI prioritizes both extreme clinical utility and a premium user experience.

## ✨ Key Features

- **🧠 Clinical AI Diagnostics**: Automated disease prediction and personalized antibiotic recommendations using `scikit-learn` models trained on extensive clinical datasets.
- **🌍 Geospatial AMR Surveillance**: Real-time resistance mapping across India. Monitor MDR (Multi-Drug Resistant) pathogens and visualize local susceptibility data via interactive maps.
- **⚕️ Deep Drug Interaction Engine**: Direct integrations with **OpenFDA** and **NLM RxNorm** to cross-reference polypharmacy cases and flag high-risk drug-drug interactions (DDI).
- **🎙️ AI Voice Narration**: Automated, acoustic voice briefings for patient cases, delivering critical clinical intelligence hands-free.
- **🔐 Secure & Compliant**: Role-based access control, secure authentication via Supabase, and clinical-grade data persistence.

---

## 🛠️ Technology Stack

**Frontend Architecture:**
- React 19 + TypeScript
- Vite (Lightning-fast HMR)
- Recharts (Clinical Data Visualization)
- Leaflet (Geospatial Mapping)
- Lucide React (Premium Iconography)
- Vanilla CSS with Glassmorphism Aesthetic

**Backend Architecture:**
- FastAPI (High-performance async Python framework)
- Uvicorn (ASGI web server)
- Scikit-Learn / Pandas / Numpy (Machine Learning Pipeline)
- Supabase (PostgreSQL & Authentication)

---

## ☁️ Deployment

Medix AI is optimized for a separated Frontend/Backend deployment model:

### 1. Frontend (Vercel)
Vercel handles the React/Vite frontend flawlessly right out of the box (with a `vercel.json` already included for client-side routing).
1. Go to [Vercel](https://vercel.com/) and click **Add New -> Project**.
2. Connect your GitHub repository.
3. Vercel will automatically detect the **Vite** framework.
4. In Environment Variables, add `VITE_API_URL` pointing to your deployed backend.
5. Click **Deploy**.

### 2. Backend (Railway)
Because Medix AI loads machine-learning models (`scikit-learn`), it is best deployed as a standard web service on Railway rather than a Serverless Function.
1. Go to [Railway](https://railway.app/) and click **New Project**.
2. Select **Deploy from GitHub repo**.
3. Choose the `medix-ai` repository.
4. Go to **Settings -> Build** and set the Root Directory to `/backend`.
5. Under **Variables**, add your `SUPABASE_URL` and `SUPABASE_KEY`.
6. Railway will automatically build the Python environment and expose the `uvicorn` server!

---

## 🛡️ License

This project is licensed under the MIT License - see the LICENSE file for details.

---
<div align="center">
  <sub>Built with ❤️ for the future of Medicine.</sub>
</div>
