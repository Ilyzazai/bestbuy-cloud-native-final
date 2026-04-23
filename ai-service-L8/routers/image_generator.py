from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from typing import Any, List, Dict
import json
import os
import requests  # Use requests for HTTP API calls

# Define the image API router
image: APIRouter = APIRouter(prefix="/generate", tags=["generate"])


# Define the Product class
class Product:
    def __init__(self, product: Dict[str, List]) -> None:
        self.name: str = product["name"]
        self.description: List[str] = product["description"]


def _use_azure_openai() -> bool:
    """Check if Azure OpenAI should be used for image generation."""
    flag = os.getenv("USE_AZURE_OPENAI", "False")
    return flag.lower() == "true"


def _generate_image_azure(name: str, description: List) -> str:
    """Generate an image using Azure OpenAI DALL-E endpoint."""
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    dalle_endpoint = os.getenv("AZURE_OPENAI_DALLE_ENDPOINT")
    dalle_deployment_name = os.getenv("AZURE_OPENAI_DALLE_DEPLOYMENT_NAME", "dall-e-3")
    api_key = os.getenv("OPENAI_DALLE_API_KEY")

    if not dalle_endpoint or not api_key:
        raise ValueError(
            "Missing required environment variables: AZURE_OPENAI_DALLE_ENDPOINT or OPENAI_DALLE_API_KEY"
        )

    target_uri = f"{dalle_endpoint}openai/deployments/{dalle_deployment_name}/images/generations?api-version={api_version}"

    headers = {"Content-Type": "application/json", "api-key": api_key}
    payload = {
        "model": "dall-e-3",
        "prompt": f"Generate a cute photo realistic image of a product in its packaging in front of a plain background for a product called <{name}> with a description <{description}> to be sold in an online pet supply store",
        "n": 1,
    }

    response = requests.post(target_uri, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    return result["data"][0]["url"]


def _generate_image_openai(name: str, description: List) -> str:
    """Generate an image using the direct OpenAI DALL-E API."""
    api_key = os.getenv("OPENAI_DALLE_API_KEY")
    dalle_model = os.getenv("OPENAI_DALLE_MODEL_NAME", "dall-e-3")

    if not api_key:
        raise ValueError("Missing required environment variable: OPENAI_DALLE_API_KEY")

    target_uri = "https://api.openai.com/v1/images/generations"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": dalle_model,
        "prompt": f"Generate a cute photo realistic image of a product in its packaging in front of a plain background for a product called <{name}> with a description <{description}> to be sold in an online pet supply store",
        "n": 1,
    }

    response = requests.post(target_uri, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    return result["data"][0]["url"]


# Define the post_image endpoint
@image.post("/image", summary="Get image for a product", operation_id="getImage")
async def post_image(request: Request) -> JSONResponse:
    try:
        # Parse the request body and create a Product object
        body: dict = await request.json()
        product: Product = Product(body)
        name: str = product.name
        description: List = product.description

        if _use_azure_openai():
            print("Calling Azure OpenAI DALL-E")
            image_url = _generate_image_azure(name, description)
        else:
            print("Calling OpenAI DALL-E")
            image_url = _generate_image_openai(name, description)

        # Return the image as a JSON response
        return JSONResponse(
            content={"image": image_url}, status_code=status.HTTP_200_OK
        )
    except Exception as e:
        # Return an error message as a JSON response
        return JSONResponse(
            content={"error": str(e)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
