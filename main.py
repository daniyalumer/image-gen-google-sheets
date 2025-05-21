"""
Yoga Pose Image Generator
-------------------------
This script reads yoga pose data from a Google Sheet, generates images for each pose
using an AI image generation API, and then inserts the images back into the sheet.

Dependencies:
- google-auth
- google-auth-oauthlib
- google-api-python-client
- requests
- python-dotenv
- Pillow

Author: Daniyal Umer Haral
Date: May 20, 2025
"""

import os
import io
import base64
import time
import json
import argparse
from urllib.parse import urlparse
import logging
from typing import List, Dict, Any, Tuple, Optional

import requests
from dotenv import load_dotenv
from PIL import Image
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up scopes for Google Sheets and Drive API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate AI images for yoga poses and insert them into Google Sheets')
    parser.add_argument('--sheet_id', type=str, help='Google Sheet ID')
    parser.add_argument('--api', type=str, default='ideogram', choices=['openai', 'ideogram', 'stability'],
                        help='AI image generation API to use (default: ideogram)')
    return parser.parse_args()

def authenticate_google() -> Credentials:
    """Authenticate with Google APIs using a service account."""
    from google.oauth2 import service_account
    
    # Path to the service account key file
    SERVICE_ACCOUNT_FILE = 'service_account.json'
    
    # Check if service account credentials file exists
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logger.error(f"Service account file {SERVICE_ACCOUNT_FILE} not found.")
        raise FileNotFoundError(f"Service account key file {SERVICE_ACCOUNT_FILE} is missing")
    
    try:
        # Create credentials from service account file
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, 
            scopes=SCOPES
        )
        logger.info("Successfully authenticated using service account")
        return creds
    except Exception as e:
        logger.error(f"Error authenticating with service account: {e}")
        raise

def get_sheet_data(sheet_id: str, credentials: Credentials) -> List[Dict[str, Any]]:
    """
    Retrieve yoga pose data from the specified Google Sheet.
    
    Args:
        sheet_id: ID of the Google Sheet
        credentials: Google API credentials
    
    Returns:
        List of dictionaries containing yoga pose data
    """
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    
    # Get sheet data
    result = sheet.values().get(
        spreadsheetId=sheet_id,
        range='Sheet1!A1:E'  # Adjust range as needed
    ).execute()
    
    values = result.get('values', [])
    if not values:
        logger.error('No data found in sheet')
        return []
    
    # Convert to list of dictionaries
    headers = values[0]
    data = []
    for row in values[1:]:
        # Ensure row has enough elements
        row_extended = row + [''] * (len(headers) - len(row))
        data.append(dict(zip(headers, row_extended)))
    
    return data

def craft_prompt(pose_data: Dict[str, Any]) -> str:
    """
    Create an optimized prompt for AI image generation based on yoga pose data.
    
    Args:
        pose_data: Dictionary containing yoga pose data
    
    Returns:
        Optimized prompt string
    """
    style = pose_data.get('Image Style', '')
    bg_color = pose_data.get('Background Color', '')
    theme = pose_data.get('Theme Description', '')
    pose = pose_data.get('Content Title', '')
    
    # Create a detailed prompt that combines all elements
    prompt = f"{style} {pose} yoga pose, {bg_color} background. {theme}"
    
    # Clean up the prompt
    prompt = prompt.replace('None', '').replace('  ', ' ').strip()
    
    logger.info(f"Generated prompt for {pose}: {prompt}")
    return prompt

def generate_image_openai(prompt: str) -> Optional[bytes]:
    """
    Generate an image using OpenAI's DALL-E API.
    
    Args:
        prompt: Image generation prompt
    
    Returns:
        Image data as bytes if successful, None otherwise
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OpenAI API key not found in environment variables")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "b64_json"
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        # Extract base64 image data
        result = response.json()
        image_data = result["data"][0]["b64_json"]
        return base64.b64decode(image_data)
    
    except Exception as e:
        logger.error(f"Error generating image with OpenAI: {e}")
        return None

def generate_image_ideogram(prompt: str) -> Optional[bytes]:
    """
    Generate an image using Ideogram API.
    
    Args:
        prompt: Image generation prompt
    
    Returns:
        Image data as bytes if successful, None otherwise
    """
    api_key = os.getenv('IDEOGRAM_API_KEY')
    if not api_key:
        logger.error("Ideogram API key not found in environment variables")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "prompt": prompt,
        "style": "illustration",  # Appropriate for yoga pose illustrations
        "aspect_ratio": "1:1"
    }
    
    try:
        # Generate the image
        response = requests.post(
            "https://api.ideogram.ai/api/v1/generation",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        # Get generation ID
        result = response.json()
        generation_id = result.get("generation_id")
        
        if not generation_id:
            logger.error("No generation ID returned from Ideogram API")
            return None
        
        # Poll for result
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(2)  # Wait before checking
            
            status_response = requests.get(
                f"https://api.ideogram.ai/api/v1/generation/{generation_id}",
                headers=headers
            )
            status_response.raise_for_status()
            
            status_data = status_response.json()
            if status_data.get("state") == "completed":
                # Download the image
                image_url = status_data.get("image_url")
                if image_url:
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        return img_response.content
                break
        
        logger.error("Image generation timed out or failed")
        return None
    
    except Exception as e:
        logger.error(f"Error generating image with Ideogram: {e}")
        return None

def generate_image_stability(prompt: str) -> Optional[bytes]:
    """
    Generate an image using Stability AI API.
    
    Args:
        prompt: Image generation prompt
    
    Returns:
        Image data as bytes if successful, None otherwise
    """
    api_key = os.getenv('STABILITY_API_KEY')
    if not api_key:
        logger.error("Stability AI API key not found in environment variables")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "text_prompts": [
            {
                "text": prompt,
                "weight": 1.0
            }
        ],
        "cfg_scale": 7,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30
    }
    
    try:
        response = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        if "artifacts" in result and len(result["artifacts"]) > 0:
            image_data = result["artifacts"][0]["base64"]
            return base64.b64decode(image_data)
        
        logger.error("No image artifacts returned from Stability API")
        return None
    
    except Exception as e:
        logger.error(f"Error generating image with Stability AI: {e}")
        return None

def generate_image(prompt: str, api: str) -> Optional[bytes]:
    """
    Generate an image using the specified API.
    
    Args:
        prompt: Image generation prompt
        api: Name of the API to use ('openai', 'ideogram', or 'stability')
    
    Returns:
        Image data as bytes if successful, None otherwise
    """
    api_functions = {
        'openai': generate_image_openai,
        'ideogram': generate_image_ideogram,
        'stability': generate_image_stability
    }
    
    if api not in api_functions:
        logger.error(f"Unsupported API: {api}")
        return None
    
    return api_functions[api](prompt)

def upload_image_to_drive(image_data: bytes, filename: str, credentials: Credentials) -> str:
    """
    Upload an image to Google Drive and return its URL.
    
    Args:
        image_data: Image binary data
        filename: Name for the image file
        credentials: Google API credentials
    
    Returns:
        URL of the uploaded image in a format suitable for Google Sheets IMAGE() formula
    """
    service = build('drive', 'v3', credentials=credentials)
    
    file_metadata = {
        'name': filename,
        'mimeType': 'image/png'
    }
    
    media = MediaIoBaseUpload(
        io.BytesIO(image_data),
        mimetype='image/png',
        resumable=True
    )
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id,webContentLink'  # Request webContentLink instead of webViewLink
    ).execute()
    
    # Set file to be publicly viewable
    service.permissions().create(
        fileId=file.get('id'),
        body={'type': 'anyone', 'role': 'reader'},
        fields='id'
    ).execute()
    
    # Get the direct download link and clean it up for IMAGE formula
    download_link = file.get('webContentLink', '')
    
    # If we got a webContentLink, clean it up
    # Remove the "download" query parameter to make it work as a direct image URL
    download_link = download_link.replace('&export=download', '')
    print("IF STATEMENT",download_link)

    logger.info(f"Created image URL: {download_link}")
    
    return download_link

def update_sheet_with_image(sheet_id: str, row: int, image_url: str, credentials: Credentials) -> None:
    """
    Update a cell in the Google Sheet with an image formula.
    
    Args:
        sheet_id: ID of the Google Sheet
        row: Row number (1-based) to update
        image_url: URL of the image to insert
        credentials: Google API credentials
    """
    service = build('sheets', 'v4', credentials=credentials)
    
    # Create IMAGE formula
    formula = f'=IMAGE("{image_url}", 3)'
    
    # Update the cell in column E
    range_name = f'Sheet1!E{row+1}'  # +1 because rows are 1-indexed in sheets
    
    body = {
        'values': [[formula]]
    }
    
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    
    logger.info(f"Updated cell {range_name} with image")

def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get Google Sheet ID from arguments or prompt
    sheet_id = args.sheet_id
    if not sheet_id:
        sheet_id = input("Enter Google Sheet ID: ")
    
    # Choose API
    api = args.api
    print(f"Using {api.upper()} API for image generation")
    
    # Authenticate with Google
    credentials = authenticate_google()
    
    # Get data from sheet
    yoga_poses = get_sheet_data(sheet_id, credentials)
    logger.info(f"Retrieved {len(yoga_poses)} yoga poses from sheet")
    
    # Process each pose
    for i, pose_data in enumerate(yoga_poses):
        pose_name = pose_data.get('Content Title', '')
        if not pose_name:
            continue
        
        logger.info(f"Processing pose {i+1}/{len(yoga_poses)}: {pose_name}")
        
        # Create prompt for image generation
        prompt = craft_prompt(pose_data)
        
        # Generate image
        logger.info(f"Generating image for {pose_name}...")
        image_data = generate_image(prompt, api)
        
        if image_data:
            # Upload image to Google Drive
            filename = f"yoga_{pose_name.lower().replace(' ', '_')}.png"
            image_url = upload_image_to_drive(image_data, filename, credentials)
            
            # Update sheet with image
            update_sheet_with_image(sheet_id, i+1, image_url, credentials)
            
            logger.info(f"Successfully processed {pose_name}")
        else:
            logger.error(f"Failed to generate image for {pose_name}")
    
    logger.info("Process completed!")

if __name__ == "__main__":
    main()