## Introduction

This project is a **Flask-based backend service** for **natural language processing (NLP) text analysis** (e.g., news, MBTI, etc.), integrated with **Anthropic LLM (Claude)** and **AWS services** to build a **Retrieval-Augmented Generation (RAG)** system.  

It allows users to upload data for **chunking** and subsequent **question-answering** through **OpenSearch Serverless/Provisioned** search, followed by **generative responses** using **Claude Sonnet/Haiku**.  

The system is **modularized**, including components for:
- Pre-configured **AWS policies and roles automation**  
- **Data preprocessing** and management  

> ⚠️ **Note:** This software is **not intended for production or commercial use**. It is designed **solely for research and demonstration purposes**.

---

## Quick Start

### Requirements
- Python IDE  
- Python 3.10+  
- AWS Bedrock Knowledge Base  
- AWS Bedrock Execution Role  
- Serverless configuration for:
  - Encryption policy  
  - Network policy  
  - Access policy  
- Attach the Bedrock Execution Role  
- Create an **S3 bucket**  
- Create an **OpenSearch collection**  
- Create an **OpenSearch index**  
- Upload data and apply **chunking** as needed  

### Recommended Package Versions
```bash
boto3==1.33.2
botocore==1.33.2
opensearch==2.3.1
```

## Installation

### 1. Clone the repository
git clone <repository-url>
cd <your-project>

### 2. Create a virtual environment (conda or others)
conda create -n rag-system python=3.10
conda activate rag-system

### 3. Configure your API keys and run
python model_pipline.py
