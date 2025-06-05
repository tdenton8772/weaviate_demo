import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.util import generate_uuid5
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_distances
import numpy as np
from weaviate.classes.query import Filter
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load .env and OpenAI key
load_dotenv()

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_APIKEY"),
)

# CONFIG
NUM_CLUSTERS = 20
VECTOR_NAME = "product_vector"

client = weaviate.connect_to_local(
    port=8080,
    grpc_port=50051,
    additional_config=AdditionalConfig(
        timeout=Timeout(init=30, query=60, insert=120)
    )
)

try:
    print("Fetching product vectors")
    product_collection = client.collections.get("Product")
    products = list(product_collection.iterator(include_vector=True))

    vectors = []
    uuids = []
    for p in products:
        vec = p.vector
        if isinstance(vec, dict):
            vec = vec['default']
        if vec:
            vectors.append(vec)
            uuids.append(p.uuid)

    print(f"📦 Found {len(vectors)} product vectors")

    # Analyze distance distribution
    dist_matrix = cosine_distances(np.array(vectors))
    print("Max distance:", np.max(dist_matrix))
    print("Min distance (non-zero):", np.min(dist_matrix[np.nonzero(dist_matrix)]))
    print("Mean distance:", np.mean(dist_matrix))

    kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(np.array(vectors))

    category_collection = client.collections.get("Category")
    category_collection.data.delete_many(where=Filter.by_property("name").like("*"))
    print("🧹 Deleted all existing Category entries")

    name_to_uuid = {}
    cluster_id_map = {}

    for i in range(NUM_CLUSTERS):
        centroid = kmeans.cluster_centers_[i]

        nearest = product_collection.query.near_vector(
            near_vector=centroid,
            limit=5
        )
        sample_titles = [x.properties["name_title"] for x in nearest.objects]

        # Prompt the LLM
        prompt = (
            "Given these product titles, suggest a concise 1–2 word category name:\n\n" +
            "\n".join(f"- {title}" for title in sample_titles)
        )
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        category_name = response.choices[0].message.content.strip().replace(" ", "_")

        # Check for collision
        if category_name in name_to_uuid:
            uuid = name_to_uuid[category_name]
        else:
            uuid = generate_uuid5(category_name)
            category_collection.data.insert(
                properties={"name": category_name},
                uuid=uuid
            )
            name_to_uuid[category_name] = uuid

        cluster_id_map[i] = uuid
        print(f"Cluster {i+1}: {category_name} → {uuid}")

    for uuid, label in zip(uuids, labels):
        product_collection.data.update(
            uuid=uuid,
            references={"category_reference": cluster_id_map[label]}
        )

    print(f"Linked all products to their Category")

finally:
    client.close()
    print("Weaviate client connection closed.")
