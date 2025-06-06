# cli_example.py

import argparse
import os
from dotenv import load_dotenv
import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.collections.classes.filters import Filter
from weaviate.classes.query import QueryReference
from openai import OpenAI

load_dotenv()

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_APIKEY"),
)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def connect_client():
    return weaviate.connect_to_local(
        port=8080,
        grpc_port=50051,
        additional_config=AdditionalConfig(
            timeout=Timeout(init=30, query=60, insert=60)
        )
    )

def generate_product_description(product: dict) -> str:
    prompt = f"""
    You are a product copywriter for an e-commerce store. Please write a compelling and SEO-optimized product description using the following details:
    """
    if 'name_title' in product.keys():
        prompt += f"\n Product Name: {product.get('name_title')}"
    if 'brand' in product.keys():
        prompt += f"\n Brand: {product.get('brand')}"
    if 'sale_price' in product.keys():
        prompt += f"\n Price: {product.get('sale_price')}"
    if 'description' in product.keys():
        prompt += f"\n Original Description: {product.get('description')}"

    prompt += f"""Avoid repeating the original exactly. Make it engaging and easy to read for customers browsing online.
                    Limit 10 50 words"""
    prompt.strip()
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating description: {e}"
    
def semantic_search(query: str, top_k: int = 5, index_name: str = "combined"):
    client = connect_client()
    try:
        collection = client.collections.get("Product")
        results = collection.query.near_text(query=query, target_vector=index_name, limit=top_k)

        if not results.objects:
            print(f"No products matched query: {query}")
            return

        print(f"\nTop {top_k} results for: '{query}'\n")
        uuid_lookup = {}
        for idx, obj in enumerate(results.objects, 1):
            props = obj.properties
            print(f"{idx}. {props.get('name_title')} - {props.get('brand')} - ${props.get('sale_price')}")
            uuid_lookup[str(idx)] = obj.uuid

        selection = input("\nSelect a product by number for more details (or press Enter to cancel): ").strip()
        if selection in uuid_lookup:
            selected_uuid = uuid_lookup[selection]
            selected_product = collection.query.fetch_object_by_id(selected_uuid)
            clear_screen()
            print("Selected Product Details:")
            print(f"{selected_product.properties.get('name_title')}")
            gen_description = generate_product_description(selected_product.properties)
            print(gen_description)
        else:
            print("No product selected or invalid input.")

    finally:
        client.close()

def list_by_category(user_query: str, top_k: int = 20):
    client = connect_client()
    try:
        # 1. Semantic search over Category
        category_collection = client.collections.get("Category")
        category_results = category_collection.query.near_text(user_query, limit=1)

        if not category_results.objects:
            print(f"No category matched query: {user_query}")
            return

        best_category = category_results.objects[0]
        category_uuid = best_category.uuid
        category_name = best_category.properties.get("name", "Unknown")

        # 2. Filter Product collection by category_reference.uuid
        product_collection = client.collections.get("Product")

        results = product_collection.query.fetch_objects(
            filters=Filter.by_ref("category_reference").by_id().equal(category_uuid),
            limit=top_k,
            return_references=QueryReference(
                link_on="category_reference",
                return_properties=["name"]
            )
        )

        if not results.objects:
            print(f"No products found in category '{category_name}'")
            return

        print(f"\nProducts in category: '{category_name}'\n")
        uuid_lookup = {}
        for idx, obj in enumerate(results.objects, 1):
            props = obj.properties
            print(f"{idx}. {props.get('name_title')} - {props.get('brand')} - ${props.get('sale_price')}")
            uuid_lookup[str(idx)] = obj.uuid

        selection = input("\nSelect a product by number for more details (or press Enter to cancel): ").strip()
        if selection in uuid_lookup:
            selected_uuid = uuid_lookup[selection]
            selected_product = product_collection.query.fetch_object_by_id(selected_uuid)
            clear_screen()
            print("Selected Product Details:")
            print(f"{selected_product.properties.get('name_title')}")
            gen_description = generate_product_description(selected_product.properties)
            print(gen_description)
        else:
            print("No product selected or invalid input.")

    finally:
        client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weaviate Product Search CLI")
    subparsers = parser.add_subparsers(dest="command")

    # semantic search
    search_parser = subparsers.add_parser("search", help="Semantic product search")
    search_parser.add_argument("query", type=str, help="Search text")
    search_parser.add_argument("--top_k", type=int, default=5, help="Number of results to return")

    # list by category
    cat_parser = subparsers.add_parser("category", help="List products by category")
    cat_parser.add_argument("name", type=str, help="Category name")
    cat_parser.add_argument("--top_k", type=int, default=5, help="Number of results to return")

    # list by category
    title_parser = subparsers.add_parser("title", help="Semantic Search of Product Name")
    title_parser.add_argument("query", type=str, help="Category name")
    title_parser.add_argument("--top_k", type=int, default=5, help="Number of results to return")

    # list by category
    cat_parser = subparsers.add_parser("description", help="Semantic Search of Product Description")
    cat_parser.add_argument("query", type=str, help="Description Phrase")
    cat_parser.add_argument("--top_k", type=int, default=5, help="Number of results to return")

    args = parser.parse_args()

    if args.command == "search":
        semantic_search(args.query, args.top_k)
    elif args.command == "category":
        list_by_category(args.name, args.top_k)
    elif args.command == "title":
        semantic_search(args.query, args.top_k, "name_title")
    elif args.command == "description":
        semantic_search(args.query, args.top_k, "description")
    else:
        parser.print_help()
