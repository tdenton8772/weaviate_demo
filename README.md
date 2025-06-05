# Weaviate Demo: Semantic Product Categorization

This demo shows how to use [Weaviate](https://weaviate.io/) with local vectorization to ingest an e-commerce catalog and auto-categorize products using unsupervised clustering. No predefined taxonomy required.

## Tech Stack

- **Weaviate** (vector database)
- **text2vec-transformers** (local vectorizer module)
- **sentence-transformers-paraphrase-MiniLM-L6-v2** (embedding model)
- **OpenAI Generative Module** (optional, for product descriptions or summaries)
- **Scikit-Learn** (for KMeans clustering)
- **Python** for data loading and categorization
- **Docker Compose** for orchestration

---

## Getting Started

### 1. Clone the Repo

```bash
git clone https://github.com/tdenton8772/weaviate_demo.git
cd weaviate_demo
```

### 2. Install Python Dependencies
It's recommended to use a virtual environment:

```bash
pyenv virtualenv 3.11.8 weviate-demo
pyenv activate weviate-demo
pip install -r requirements.txt

# If requirements.txt is missing, install manually:

pip install weaviate-client scikit-learn numpy
```

### 3. Start Weaviate with Local Vectorizer
```bash
docker-compose up
```

This will launch:

- weaviate (on port 8080)
- text2vec-transformers with MiniLM-L6-v2 (on port 8000)

Wait until http://localhost:8080/v1/.well-known/ready returns 200 OK.

## Demo Scripts
### 1. load_data.py
Loads product catalog data from:

- jcpenney_com-ecommerce_sample.csv

It creates two Weaviate collections:

- Product: Stores all product info
- Category: (populated later via clustering)

Run:

```bash
python load_data.py
```

### 2. categorize_data.py
Retrieves vectors from the Product collection

Performs unsupervised clustering (KMeans)

Creates synthetic Cluster_XX categories

Links products to clusters via a category_reference field

Run:

```bash
python categorize_data.py
```

This script will delete existing category data before re-clustering.

Querying Weaviate
You can explore the vectorized catalog and relationships using the Weaviate Python client or GraphQL.

Example: Find similar products
```bash
result = client.query.get("Product", ["name_title", "category"]) \
    .with_near_text({"concepts": ["stand mixer"]}) \
    .with_limit(5) \
    .do()
```