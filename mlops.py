from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from tensorflow.keras.preprocessing.image import img_to_array
import numpy as np
import tensorflow as tf
from PIL import Image
import io
from tensorflow.keras.models import load_model
from fastapi.middleware.cors import CORSMiddleware
from nosql_table import Images
import boto3
from botocore.exceptions import ClientError, BotoCoreError
import datetime
import random
import traceback
from decimal import Decimal
from pydantic import BaseModel
import os

app = FastAPI()
   
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)


#defining and loading the model and its config
IMG_SIZE = (160, 160)
CLASS_NAMES = ['Cardboard', 'Food','Glass','Metal','Miscellaneous','Paper','Plastic','Textile','Vegetation']
model = load_model('best_resnet101_model.keras')

# AWS variables
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# suffix for the image : to distinguish each images if the name is same
time_suffix = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# DynamoDB table configuration
table_name = "waste-classification-images-metadata"
dyn_resource = boto3.resource('dynamodb', region_name = AWS_REGION)
dynamodb_table = dyn_resource.Table(table_name)

# check if the directory already exists?
def mkdirs(file_path):
    if not os.path.exists(file_path):
        os.makedirs(file_path, exist_ok = True)

# EFS configuration
EFS_MOUNT_POINT = "/mnt/efs"
IMAGE_DIRECTORY = os.path.join(EFS_MOUNT_POINT, "images")
mkdirs(IMAGE_DIRECTORY)


# model's input preprocessing stuff
def preprocessing(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize(IMG_SIZE)
    img_array = img_to_array(image)
    img_array = tf.cast(img_array, tf.float32)
    img_array = tf.expand_dims(img_array, axis=0)
    return img_array

# health check for the load balancer
@app.get('/health')
async def health_check():
    return JSONResponse(content={"status": "healthy"})

# temp storing the image for frontend-backend issue:
last_uploaded_images = {}

# predict post route
@app.post('/predict')
async def predict(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = preprocessing(contents)
        
        # image name and its path for EFS
        image_name = f"{time_suffix}_{random.randint(1,10000)}_{file.filename}"
        last_uploaded_images[file.filename] = image_name
        image_path = os.path.join(IMAGE_DIRECTORY, image_name)
        
        # saving the image on EFS
        try:
            with open(image_path, 'wb') as f:
                f.write(contents) # contents here refers to the image uploaded by the user, not the image variable from above which is an array
            print(f"Image '{image_name}' saved to EFS at '{image_path}'")
        except Exception as err:
            return JSONResponse(status_code=500, content={"error": str(err)})   
        
        # prediction logic stuff
        y_hat = model.predict(image)
        predicted_class = np.argmax(y_hat[0])
        confidence = float(np.max(y_hat[0]))
        
        #intializing the DynamoDB table resource, if it doesn't not exist, it will create a new table
        img_object = Images(dyn_resource)
        img_table_exists = img_object.exists(table_name)
        if not img_table_exists:
            print(f"\n Creating table {table_name}")
            img_object.create_table(table_name)
        
        img_object.add_image(
                    image_name=image_name,
                    image_efs_path=image_path,
                    model_prediction_class=CLASS_NAMES[predicted_class],
                    model_confident_score=Decimal(str(confidence)),
                    user_selected_label_answer_choice="",
                    user_selected_label_boolean="",
                    image_upload_date=str(datetime.datetime.now().date())
                )
        
        return JSONResponse({
            "filename": file.filename,
            "image_name": image_name,
            "predicted_class": int(predicted_class),
            "class_name": CLASS_NAMES[predicted_class],
            "confidence": confidence
        })
    
    except Exception as e:
        print("Internal error:")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

class FeedbackItem(BaseModel):
    image_name: str
    user_selected_label_boolean: str
    user_selected_label_answer_choice: str
    
@app.post("/save-feedback")
async def save_feedback(item: FeedbackItem):
    """
    Receives user feedback and updates the corresponding record in DynamoDB.
    """
    try:
        # Update the existing item in DynamoDB with the user's feedback
        response = dynamodb_table.update_item(
            Key={'image_name': item.image_name},
            UpdateExpression="SET user_selected_label_boolean = :b, user_selected_label_answer_choice = :c",
            ExpressionAttributeValues={
                ':b': item.user_selected_label_boolean,
                ':c': item.user_selected_label_answer_choice,
            },
            ReturnValues="UPDATED_NEW"
        )
        return {"message": "Feedback saved successfully.", "updatedAttributes": response.get('Attributes', {})}
        
    except ClientError as e:
        print(f"AWS Client Error during feedback save: {e}")
        raise HTTPException(status_code=500, detail=f"Could not update feedback for {item.image_name}.")
    except Exception as e:
        print(f"An unexpected error occurred during feedback save: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred while saving feedback.")

    