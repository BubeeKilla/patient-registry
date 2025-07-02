# 🩺 Patient Registry - Flask, Docker, Pulumi, AWS

A simple, production-ready Patient Registry web app built with:

- 🐍 **Flask** for backend  
- 🐳 **Docker** containerization  
- 🛠️ **Pulumi** for Infrastructure as Code  
- ☁️ **AWS ECS Fargate** deployment  
- 🗄️ SQLite (local) or RDS (coming soon) for persistent storage  
- 🔒 Basic admin authentication  

---

## 🚀 Features

- Add, edit, delete patient records  
- Search functionality  
- Pagination & sorting  
- Basic admin login required to access registry  
- Server-side inactivity logout  
- Fully containerized & cloud deployed  
- CI/CD ready with GitHub Actions  

---

## ⚡ Quick Start (Local)

### Prerequisites

- Python 3.12+  
- Docker  
- Pulumi CLI  
- AWS credentials (for deployment)  

### Run Locally

```bash
# Install Python dependencies
pip install -r requirements.txt

# Initialize DB and run Flask app
python app.py
```

Visit [http://localhost:5000](http://localhost:5000)  

Default admin credentials:

```
Username: admin  
Password: password  
```

---

## ☁️ Deploy to AWS

1. Configure Pulumi with your AWS credentials  
2. Build & deploy:

```bash
pulumi up
```

Pulumi provisions:

- VPC & networking  
- Security groups  
- ECS Cluster & Fargate Service  
- Docker image build & push to ECR  
- Task Definition & Service deployment  

---

## 🔄 CI/CD Pipeline

This project includes a **GitHub Actions** workflow to redeploy automatically on every push to `main`.

### Required GitHub Secrets:

- `AWS_ACCESS_KEY_ID`  
- `AWS_SECRET_ACCESS_KEY`  
- `PULUMI_ACCESS_TOKEN`  

---

## 🛠️ Roadmap

- Replace SQLite with AWS RDS  
- Replace hardcoded login with secure user management  
- Add role-based access control  
- Extend patient model (more fields, validation)  
- Improve UI/UX  

---

## 📄 License

MIT — use, modify & deploy freely.