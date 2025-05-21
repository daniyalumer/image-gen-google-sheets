# Yoga Pose Image Generator

> **Note:** Currently, OpenAI DALL-E is the only image generation API that has been fully tested with this application. Support for Ideogram and Stability AI is included but has not been extensively validated.

This application automatically generates AI images for yoga poses based on data from a Google Sheet and inserts the images back into the sheet.

## Features

- Reads yoga pose data from Google Sheets
- Generates optimized prompts for AI image generation
- Supports multiple AI image generation APIs (OpenAI DALL-E, Ideogram, Stability AI)
- Uploads generated images to Google Drive
- Inserts images back into the Google Sheet using IMAGE() formulas

## Requirements

### Python Dependencies

```
google-auth>=2.22.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.100.0
requests>=2.31.0
python-dotenv>=1.0.0
Pillow>=10.0.0
```

### API Keys and Authentication

1. **Google Sheets/Drive API**:
   - Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Google Sheets API and Google Drive API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials JSON file and save it as `service_account.json` in the project directory

2. **Image Generation API** (choose one or more):
   - **OpenAI DALL-E**: Get an API key from [OpenAI](https://platform.openai.com/)
   - **Ideogram**: Get an API key from [Ideogram](https://ideogram.ai/)
   - **Stability AI**: Get an API key from [Stability AI](https://stability.ai/)

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project directory with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   IDEOGRAM_API_KEY=your_ideogram_api_key
   STABILITY_API_KEY=your_stability_api_key
   ```
4. Place your Google API service account file (`service_account.json`) in the project directory

## Usage

Run the script using the following command:

```
python main.py --sheet_id YOUR_SHEET_ID --api ideogram
```

Arguments:
- `--sheet_id`: The ID of your Google Sheet (from the URL)
- `--api`: The AI image generation API to use (openai, ideogram, or stability)

## Expected Sheet Format

The script expects a Google Sheet with the following columns:
- Image Style
- Background Color
- Theme Description
- Content Title
- Image Generation (where images will be inserted)

## How It Works

1. The script authenticates with Google APIs using a service account
2. Reads yoga pose data from the specified Google Sheet
3. For each pose:
   - Crafts an optimized prompt based on style, background color, theme, and pose name
   - Generates an image using the selected AI API
   - Uploads the image to Google Drive with public sharing
   - Updates the Google Sheet with an IMAGE() formula pointing to the uploaded image

## API Selection Rationale

- **Ideogram**: Recommended for illustration-style images with excellent prompt adherence
- **OpenAI DALL-E**: Great all-around image quality with good understanding of yoga poses
- **Stability AI**: Good for more realistic or detailed renderings

## Error Handling

The script includes comprehensive error handling and logging for:
- API authentication failures
- Image generation errors
- Google Sheets/Drive API issues

## Limitations

- API rate limits may affect processing speed
- Image quality depends on the selected API and prompt engineering
- Service account must have appropriate access to the Google Sheet and Drive

