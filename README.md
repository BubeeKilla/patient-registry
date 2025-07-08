# 🩺 Patient Registry - Flask, Docker, Pulumi, AWS

A simple, production-grade Patient Registry web app built with:

- 🐍 **Flask** for backend  
- 🐳 **Docker** containerization  
- 🛠️ **Pulumi** for Infrastructure as Code  
- ☁️ **AWS ECS Fargate** for deployment  
- 🗄️ **AWS RDS (PostgreSQL)** for persistent storage  
- 🔐 **Role-based user access (Admin/Doctor)**  
- 🔄 **CI/CD with GitHub Actions**

---

## 🚀 Features

- Add, edit, delete patient records (admin only)  
- Search patient data (all logged-in users)  
- Flash notifications with Bootstrap styling  
- Admin login is created from GitHub Actions secrets (never hardcoded)  
- Admin can manage doctor users (create, delete, update password)  
- Protected views via role-based decorators  
- Session auto-logout after inactivity  
- Bootstrap-styled UI  
- Fully containerized & cloud deployed  
- CI/CD ready via GitHub Actions

---

## ⚡ Quick Start (Local)

### Prerequisites

- Python 3.12+  
- Docker  
- Pulumi CLI  
- AWS credentials (for deployment)  

### Run Locally

```
pip install -r requirements.txt
python app.py
```

Visit [http://localhost:5000](http://localhost:5000)

🔐 **Admin credentials must be passed via env vars**:

```bash
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD=your_secure_pw
```

---

## ☁️ Deploy to AWS

1. Set AWS credentials & secrets (or use GitHub Actions)  
2. Deploy infrastructure & app:

```bash
pulumi config set aws:region eu-central-1
pulumi config set --secret adminUsername "your_admin_user"
pulumi config set --secret adminPassword "your_admin_password"
pulumi up
```

Pulumi provisions:

- VPC + public subnets  
- Security groups  
- ECS Cluster + Service  
- PostgreSQL RDS instance  
- Docker image build & push to ECR  
- Injected ENV vars into ECS Task (DB + Admin creds)

🧠 **Admin credentials are passed as env vars and not hardcoded**.

---

## 🔄 CI/CD with GitHub Actions

This project auto-deploys on every push to `main`.

### Required GitHub Secrets:

- `AWS_ACCESS_KEY_ID`  
- `AWS_SECRET_ACCESS_KEY`  
- `PULUMI_ACCESS_TOKEN`  
- `ADMIN_USERNAME`  
- `ADMIN_PASSWORD`  
- `DB_HOST`
- `DB_NAME_PG`  
- `DB_USER`  
- `DB_PASSWORD`  

---

## 🛠️ Roadmap

- Add audit logging  
- Add email notifications for password changes  
- Add patient history timeline  
- Graphs for patient conditions  
- Monitoring & alerting (Grafana/Prometheus)

---

## 📄 License

MIT — use, modify & deploy freely.