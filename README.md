Medix AI

AI-powered antimicrobial decision support

Medix AI is a clinical decision-support platform built to help healthcare professionals make more informed antibiotic decisions by bringing patient context, drug information, drug interactions, and the most recent available regional antimicrobial-resistance data into one place.

The idea behind Medix is simple: instead of searching through multiple sources before making a treatment decision, relevant information should be available together and presented in a way that is easy to understand.



Why Medix AI?

Antimicrobial resistance (AMR) is becoming increasingly difficult to manage, and resistance patterns can vary significantly across regions.

At the same time, choosing an antibiotic is not only about resistance. Patient information, existing medications, possible drug interactions, and other clinical factors also need to be considered.

Medix AI brings these factors together to provide contextual, explainable decision support.

The system is designed to assist clinicians, not replace them.



What Medix AI Does

Medix AI combines:

- Patient-specific information
- Antibiotic and medication data
- Drug-interaction information
- Regional antimicrobial-resistance data
- Machine-learning analysis
- Treatment comparison and explainable insights

A user can provide a region and antibiotic context and view the most recent available resistance information through an interactive map.



Regional AMR Map

The map provides a visual representation of reported resistance levels:

 Green— Lower reported resistance
 Yellow— Moderate reported resistance
 Red — Higher reported resistance

The map is based on the most recent available data from the connected sources. It does **not** represent real-time resistance measurements from an individual patient.

 Key Features

 AI-assisted analysis-

The machine-learning layer analyzes structured project data to support the overall decision-support workflow.

Drug interaction checking-

Medication information is used to identify potential drug-interaction concerns that may be relevant to a treatment option.

Regional AMR intelligence-

Resistance information is connected with geographical context, allowing users to understand how reported resistance varies by region.

 Treatment comparison-

Different treatment options can be explored and compared using the information available to the system.

 Explainable insights-

Rather than presenting an unexplained prediction, Medix AI aims to show the factors and information behind its insights.

 Human-in-the-loop-

The doctor remains the final decision-maker. Medix AI provides supporting information rather than making autonomous prescribing decisions.



Data & Integrations

Medix AI combines project-specific datasets with external healthcare information sources.

RxNav / RxNorm-
Used for structured drug and medication information.

National Library of Medicine (NLM)-
Used as a source of biomedical and medication-related information.

WHO GLASS-
Provides antimicrobial-resistance surveillance data used within the AMR intelligence layer.

Project CSV datasets-
Used for training and evaluating the machine-learning components of the project.

The quality and availability of results depend on the coverage and recency of the underlying datasets and external sources.



How It Works

The workflow is straightforward:

1. Enter the relevant patient and medication information.
2. Select the geographical region.
3. Provide the antibiotic or treatment being considered.
4. Medix AI processes the available clinical, medication and AMR information.
5. The system presents resistance information, interaction insights and treatment comparisons.
6. The healthcare professional reviews the information and makes the final decision.



Technology

Medix AI consists of four main components:

Frontend — Clinical dashboard, treatment interface and interactive AMR map.

Backend — API integration, data processing and application logic.

Machine Learning— Uses Random Forest algorithm, preprocessing and inference using structured datasets.

External Data Layer — Drug, medication and antimicrobial-resistance information from connected healthcare sources.



B2B Revenue Model

Medix AI follows a B2B SaaS model, selling antimicrobial decision-support capabilities to healthcare organizations rather than individual patients.

Revenue Streams

Hospital & Clinic Subscriptions — Recurring monthly/annual plans based on organization size, users, and usage.

Enterprise Licensing — Custom contracts for hospital networks, diagnostic groups, and large healthcare organizations requiring organization-wide deployment.

API & Data Access — Usage-based pricing for integrating Medix AI's drug-interaction, AMR intelligence, and decision-support capabilities into existing clinical systems.

Premium Analytics — Paid dashboards and reporting for AMR trends, antibiotic utilization, and regional resistance intelligence.
Implementation & Integration — One-time fees for EHR/HIS integration, onboarding, customization, and deployment.



Project Structure

```text
medix-ai/
├── frontend/
├── backend/
├── ml/
├── data/
├── docs/
├── requirements.txt
├── package.json
└── README.md
