import os
from PIL import Image
import base64
import io
import requests
from datetime import datetime
import logging
from openai import OpenAI
import httpx
import json
from sentence_transformers import SentenceTransformer
import torch
import re
import ast  # Add to imports at top of file
import demjson3  # Add to imports at top of file

class PhotoAnalyzer:
    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # Load settings from JSON file
        with open('photogen_settings.json') as f:
            settings = json.load(f)
            
        self.client = OpenAI(
            base_url=settings["custom_server_base_url"],
            api_key=settings["custom_server_api_key"],
            http_client=httpx.Client()
        )
        self.custom_model = settings["default_models"]["custom"]
        
        # Initialize the sentence transformer model
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')  # Small, fast model that works well for semantic search

    def analyze_photo(self, photo_id, model=None):
        """Analyze a photo using the local AI model."""
        model = model or self.custom_model
        
        with self.app.app_context():
            try:
                self.logger.info(f"Starting analysis of photo {photo_id}")
                from server import Photo
                photo = self.db.session.get(Photo, photo_id)
                if not photo:
                    raise ValueError(f"Photo {photo_id} not found")
                
                # First attempt
                try:
                    photo_path = os.path.join(self.app.config['UPLOAD_FOLDER'], photo.filename)
                    self.logger.info(f"Processing image at {photo_path}")
                    
                    with Image.open(photo_path) as img:
                        buffer = io.BytesIO()
                        img.save(buffer, format="JPEG")
                        encoded_image = base64.b64encode(buffer.getvalue()).decode() 
                    
                    # Simplified prompt focused on clean sentence output
                    structured_prompt = """CRITICAL: You MUST return ONLY a array of descriptive sentences. DO NOT add any other text:

[
    "Brief factual description of the overall scene.",
    "The scene shows [location] with [weather/lighting conditions].",
    "There are [number] people present in the image.",
    "Key objects visible include [list 3-5 main items].",
    "Likely event such as a new years eve party, baby shower, or birthday.",
    "The image has a [mood] atmosphere with prominent [colors] colors."
]

Format Rules:
- Return ONLY the array
- Each sentence should be complete, natural, concise, and factual
- NO explanations or additional text
- Keep descriptions concise and factual
- Maintain exact format with double quotes"""

                    completion = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": structured_prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                                ]
                            }
                        ],
                        max_tokens=300
                    )
                    
                    if not completion or not completion.choices:
                        self.logger.error(f"No response received for photo {photo_id}")
                        return False
                    
                    raw_response = completion.choices[0].message.content
                    
                    # Store raw response immediately
                    photo.ai_raw_response = raw_response
                    photo.ai_analyzed_at = datetime.utcnow()
                    
                    # Parse response
                    try:
                        json_str = raw_response.strip()
                        json_str = json_str.replace('```json', '').replace('```', '')
                        
                        try:
                            sentences = demjson3.decode(json_str)
                        except Exception:
                            sentences = [
                                s.strip() + '.'
                                for s in json_str.split('.')
                                if s.strip()
                            ]
                            sentences = [s for s in sentences if s != '.']
                        
                        if not isinstance(sentences, list):
                            sentences = [str(sentences)]
                        sentences = [str(s) for s in sentences]
                        
                        photo.ai_description = sentences
                        self.db.session.commit()
                        
                        self.logger.info(f"Successfully analyzed photo {photo_id}")
                        return True

                    except Exception as e:
                        self.logger.error(f"Failed to parse response for photo {photo_id}: {str(e)}")
                        return False
                        
                except Exception as e:
                    self.logger.error(f"Analysis failed for photo {photo_id}: {str(e)}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error analyzing photo {photo_id}: {e}", exc_info=True)
                return False

    def match_photos_to_prompt(self, prompt, similarity_threshold=0.2):
        """Find photos that match a given prompt using sentence embeddings."""
        try:
            self.logger.info(f"Starting semantic photo matching with prompt: {prompt}")
            
            from server import Photo
            import torch
            
            with self.app.app_context():
                photos = self.db.session.query(Photo).filter(Photo.ai_description.isnot(None)).all()
                self.logger.info(f"Found {len(photos)} photos with AI descriptions to check")
                
                matching_photos = []
                photo_texts = []
                
                # Process all photo descriptions
                for photo in photos:
                    try:
                        self.logger.debug(f"Processing photo {photo.id}")
                        
                        # Get the list of sentences
                        description_data = photo.ai_description
                        
                        if not isinstance(description_data, list):
                            self.logger.warning(f"Unexpected description format for photo {photo.id}")
                            continue
                            
                        # Join all sentences into a single searchable text
                        photo_text = " ".join(description_data)
                        
                        self.logger.debug(f"Created description for photo {photo.id}: {photo_text[:100]}...")
                        photo_texts.append((photo, photo_text))
                        
                    except Exception as e:
                        self.logger.error(f"Error processing photo {photo.id}: {e}", exc_info=True)
                        continue
                
                self.logger.info(f"Successfully processed {len(photo_texts)} photo descriptions")
                
                if not photo_texts:
                    return []
                
                # Get embeddings for prompt
                prompt_embedding = self.encoder.encode(prompt.lower(), convert_to_tensor=True)
                
                # Process all photos at once
                texts = [text for _, text in photo_texts]
                photos_list = [photo for photo, _ in photo_texts]
                
                # Get embeddings for all texts
                self.logger.debug("Computing embeddings for all photos")
                embeddings = self.encoder.encode(texts, convert_to_tensor=True)
                
                # Ensure proper dimensions
                if len(embeddings.shape) == 1:
                    embeddings = embeddings.unsqueeze(0)
                prompt_embedding_reshaped = prompt_embedding.reshape(1, -1)
                
                # Calculate similarities
                similarities = torch.nn.functional.cosine_similarity(
                    prompt_embedding_reshaped, 
                    embeddings
                ) 
                
                # Process similarity scores
                self.logger.debug("Processing similarity scores")
                for idx, score in enumerate(similarities.cpu().numpy()):
                    score = float(score)
                    self.logger.debug(f"Photo {photos_list[idx].id} similarity score: {score:.3f}")
                    if score >= similarity_threshold:
                        matching_photos.append((photos_list[idx], score))
                        self.logger.info(f"Photo {photos_list[idx].id} matched with score: {score:.3f}")
                    else:
                        self.logger.debug(f"Photo {photos_list[idx].id} below threshold. Text: {texts[idx][:100]}...")
                
                # Sort matches by similarity score
                matching_photos.sort(key=lambda x: x[1], reverse=True)
                result = [photo for photo, _ in matching_photos]
                
                # Log results with descriptions
                self.logger.info(f"Matching completed. Found {len(result)} matching photos:")
                for photo, score in matching_photos:
                    self.logger.info(f"- Photo ID: {photo.id}, URL: {photo.filename}, Score: {score:.3f}")
                    matching_text = next(text for p, text in photo_texts if p.id == photo.id)
                    self.logger.info(f"  Description: {matching_text[:200]}...")
                
                return result
            
        except Exception as e:
            self.logger.error(f"Error in photo matching: {e}", exc_info=True)
            return []