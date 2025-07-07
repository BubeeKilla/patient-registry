# 🩺 Patient Registry - Flask, Docker, Pulumi, AWS

A simple, production-grade Patient Registry web app built with:

- 🐍 **Flask** for backend  
- 🐳 **Docker** containerization  
- 🛠️ **Pulumi** for Infrastructure as Code  
- ☁️ **AWS ECS Fargate** for deployment  
- 🗄️ **AWS RDS (PostgreSQL)** for persistent storage  
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

```
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
2. Deploy infrastructure & app:

```
pulumi up
```

Pulumi provisions:

- VPC & networking  
- Security groups  
- ECS Cluster & Fargate Service  
- AWS RDS (PostgreSQL) instance  
- Docker image build & push to ECR  
- Task Definition with injected DB credentials  
- Service deployment  

**Note:** After each new Pulumi deployment, the RDS hostname may change.  

### ✅ **Important: Update GitHub Secret `DB_HOST` manually**  
Copy the new RDS endpoint output from `pulumi up` and update your GitHub Actions Secrets before triggering CI/CD.

---

## 🔄 CI/CD Pipeline

The project includes a **GitHub Actions** workflow to redeploy automatically on every push to `main`.

### Required GitHub Secrets:

- `AWS_ACCESS_KEY_ID`  
- `AWS_SECRET_ACCESS_KEY`  
- `PULUMI_ACCESS_TOKEN`  
- `DB_HOST` (update after each Pulumi deploy)  
- `DB_NAME_PG`  
- `DB_USER`  
- `DB_PASSWORD`  

---

## 🛠️ Roadmap

- Replace hardcoded login with secure user management  
- Add role-based access control  
- Extend patient model (more fields, validation)  
- Improve UI/UX  
- Reminder: Manually update `DB_HOST` GitHub Secret after every Pulumi deploy  

---

## 📄 License

MIT — use, modify & deploy freely.
