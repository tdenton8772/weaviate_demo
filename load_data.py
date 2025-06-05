import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
import weaviate.classes.config as wvcc
from weaviate.classes.config import ReferenceProperty
import json
from weaviate.classes.query import Filter
import csv

client = weaviate.connect_to_local(
    port=8080,
    grpc_port=50051,
    additional_config=AdditionalConfig(
        timeout=Timeout(init=30, query=60, insert=120)
    )
)

try:
    client.collections.delete("Product")
except:
    pass

try:
    client.collections.delete("Category")
except: 
    pass


try:
    # create the Category collection
    if "Category" not in client.collections.list_all():
        client.collections.create(
            name="Category",
            properties=[
                wvcc.Property(name="name", data_type=wvcc.DataType.TEXT)
            ],
            vectorizer_config=wvcc.Configure.Vectorizer.text2vec_transformers()
        )
        print(f"Created collection: Category")
    else:
        print(f"Collection 'Category' already exists.")

    #create the product collection
    if "Product" not in client.collections.list_all():
        collection = client.collections.create(
            name="Product",
            # vectorizer_config=wvcc.Configure.Vectorizer.text2vec_openai(), << started out here but hit 429
            vectorizer_config=wvcc.Configure.Vectorizer.text2vec_transformers(), # switched to local transformer 
            generative_config=wvcc.Configure.Generative.openai(),
            properties=[
                wvcc.Property(name="name_title", data_type=wvcc.DataType.TEXT),
                wvcc.Property(name="brand", data_type=wvcc.DataType.TEXT),
                wvcc.Property(name="category", data_type=wvcc.DataType.TEXT),
                wvcc.Property(name="sku", data_type=wvcc.DataType.TEXT),
                wvcc.Property(name="list_price", data_type=wvcc.DataType.NUMBER),
                wvcc.Property(name="sale_price", data_type=wvcc.DataType.NUMBER),
            ],
            references=[
                ReferenceProperty(
                    name="category_reference",
                    target_collection="Category"
                )
            ]
        )
        print(f"Created collection: Product")
    else:
        print(f"Collection 'Product' already exists.")

    product_collection = client.collections.get("Product")

    # # create the product catalog entries from the jcpenny array
    # with open("catalog_array.json", "r") as f:
    #     catalog = json.load(f)
    batch = []

    with open("jcpenney_com-ecommerce_sample.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            if not row["name_title"] or not row["brand"]:
                continue  # skip incomplete rows

            uuid = row["uniq_id"] or row["sku"]
            list_price = row["list_price"].split("-")[0] or 0 # data for some reason looks like this 21.32-55.01
            sale_price = row["sale_price"].split("-")[0] or 0
            try:
                batch.append({
                    "uuid": uuid,
                    "name_title": row["name_title"],
                    "description": row["description"],
                    "brand": row["brand"],
                    "category": row["category"],
                    "sku": row["sku"],
                    "list_price": float(list_price),
                    "sale_price": float(sale_price),
                })
            except Exception as e:
                print(f"Skipped record {row.get('name_title')} due to error: {e}")

    product_collection.data.insert_many(batch)
    print(f"Inserted {len(batch)} records.")

finally:
    #apparently weaviate gets mad if you dont close the connection with the script exits
    client.close()
    print("Weaviate client connection closed.")
