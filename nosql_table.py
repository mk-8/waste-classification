import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
# import os
# import json
import logging
# from question import Question
from decimal import Decimal


logger = logging.getLogger(__name__)

class Images:
    '''
        Example data structure for an image record in a table:
        {
            "image_name" : "waste.jpg",
            "image_efs_path" : "s3_path",
            "model_prediction_class" : "class_name",
            "user_selected_label_boolean" : "True",
            "user_selected_label_answer_choice" : "one_of_9_class",
            "model_confident_score" : "57.09",
            "image_upload_date" : "05/23/2025"
        }
    '''
    
    def __init__(self, dyn_resource):
        '''
            :param dyn_resource : A Boto3 DynamoDB resource
        '''
        self.dyn_resource = dyn_resource
        # the table variable is called to verify if the table exits, else it is 
        # set by 'create_table'
        self.table = None
        
    def exists(self, table_name):
        '''
            Determines whether a table exists. 
            :param table_name: The name of the table to check
            :return: True when the table exists; otherwise, False
        '''
        try: 
            table = self.dyn_resource.Table(table_name)
            table.load()
            exists = True
        except ClientError as err:
            if err.response["Error"]["Code"] == "ResourceNotFoundException":
                exists = False
            else:
                logger.error("Couldn't check for existence of %s. Here's why: %s: %s",
                             table_name,
                             err.response["Error"]["Code"],
                             err.response["Error"]["Message"],
                             )
                raise
        else:
            self.table = table
        return exists
    
    def create_table(self, table_name):
        '''
            Creates an Amazon DynamoDB table that is used to store the Image related details 
            uploaded by the user
        '''
        try: 
            self.table = self.dyn_resource.create_table(
                TableName = table_name,
                KeySchema=[
                    {'AttributeName': 'image_name', 'KeyType': 'HASH'}  # Partition key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'image_name', 'AttributeType': 'S'}
                ],
                BillingMode = "PAY_PER_REQUEST",
            )    
            self.table.wait_until_exists()
        except ClientError as err:
            logger.error("Coudn't create a table %s, because of %s: %s",
                         table_name,
                         err.response['Error']['Code'],
                         err.response['Error']['Message']
                         )
            raise
        else:
            return self.table
        
    def list_tables(self):
        '''
            :return : the list of tables
        '''
        try:
            tables = []
            for table in self.dyn_resource.tables.all():
                print(table.name)
                tables.append(table)
        except ClientError as err:
            logger.error("Couldn't list tables because of :%s : %s",
                         err.response['Error']['Code'],
                         err.response['Error']['Message'],
                         )
            raise
        else:
            return tables

    # def write_batch(self, images):
    #     '''
    #         fills the DynamoDB table with specified data, using the Boto3 Table.batch_writer()
    #         , to put the items in the table. 
    #         Inside the context manager, Table.batch_writer builds a list of requests
    #         On Exiting the context manager, Table.batch_writer starts sendoing batches of write 
    #         requests to DynamoDB and automatically handles chunking, buffering, and retrying.
            
    #         :param Images: The data to put in the table. Each item must contain at least the 
    #                         keys required by the schema that was specified when the table was
    #                         created
    #     '''                    
        
    #     try:
    #         with self.table.batch_writer() as writer:
    #             for image in images:
    #                 writer.put_item(Item=image)
    #     except ClientError as err:
    #         logger.error(
    #             "Coudn't load data into table %s. Here's why: %s: %s",
    #             self.table.name,
    #             err.response['Error']['Code'],
    #             err.response['Error']['Message'],
    #         )
    #         raise
        
    def add_image(self, image_name, image_efs_path, model_prediction_class, user_selected_label_boolean, user_selected_label_answer_choice, 
    model_confident_score, image_upload_date):
        '''
            Adds the Image and its details
            
            :param image_name : The name of the image
            :param image_efs_path : Path to s3 bucket
            :param model_prediction_class : Model's image prediction class name
            :param user_selected_label_boolean : User selected label
            :param user_selected_label_answer_choice : User selected label if the             user_selected_label_boolean was False
            :param model_confident_score : Model's confident score
            :param image_upload_date : Image upload date

        '''
        
        try: 
            self.table.put_item(
                Item={
                    "image_name": image_name,
                    "image_efs_path": image_efs_path,
                    "model_prediction_class" : model_prediction_class,
                    "user_selected_label_boolean" : user_selected_label_boolean,
                    "user_selected_label_answer_choice": user_selected_label_answer_choice,
                    "model_confident_score": Decimal(str(model_confident_score)),
                    "image_upload_date": image_upload_date
                }
            )
        except ClientError as err:
            logger.error(
                "Coudn't add image %s to table %s because %s : %s",
                image_name,
                self.table.name,
                err.response['Error']['Code'],
                err.response['Error']['Message'],
            )
            raise
    
    def get_image(self, image_name, image_efs_path, model_prediction_class, user_selected_label_boolean):
        '''
            Gets image data from the table for a specific image.
   
            :param image_name: The name of the image
            :param image_path: Path to s3 bucket
            :param model_prediction_class: Model's image prediction class name
            :param user_selected_label_boolean: User selected label
	
        '''
        try:
            response = self.table.get_item(Key={'image_name':image_name, "image_efs_path": image_efs_path, "model_prediction_class": model_prediction_class, "user_selected_label_boolean": user_selected_label_boolean})
        except ClientError as err:
            logger.error("Couldn't get image %s from table %s because of %s : %s",
                         image_name,
                         self.table.name,
                         err.response['Error']['Code'],
                         err.response['Error']['Message'],
            )
            raise
        else:
            return response["Item"]
        
    def query_images(self, model_prediction_class):
        '''
            Queries for images that were predicted by the model
   
            :param model_prediction_class: Model's image prediction class name
            :return: the list of images that were predicted by model for a specific class
        
        '''
        
        try:
            response = self.table.query(KeyConditionExpression = Key("model_prediction_class").eq(model_prediction_class))
        except ClientError as err:
            logger.error(
                "Couldn't query the image for %s class because of %s : %s",
                model_prediction_class,
                err.response['Error']['Code'],
                err.response['Error']['Message'],
            )   
            raise
        else:
            return response['Items']
      
    
    def delete_image(self, image_name, image_efs_path, model_prediction_class, user_selected_label_boolean, user_selected_label_answer_choice, 
    model_confident_score, image_upload_date):
        '''
            Deletes the Image and its details from the table
            
            :param image_name : The name of the image
            :param image_efs_path : Path to s3 bucket
            :param model_prediction_class : Model's image prediction class name
            :param user_selected_label_boolean : User selected label
            :param user_selected_label_answer_choice : User selected label if the             user_selected_label_boolean was False
            :param model_confident_score : Model's confident score
            :param image_upload_date : Image upload date

        '''
        
        try: 
            self.table.delete_item(
                Key={
                    "image_name": image_name,
                }
            )
        except ClientError as err:
            logger.error(
                "Coudn't delete image %s to table %s because %s : %s",
                image_name,
                self.table.name,
                err.response['Error']['Code'],
                err.response['Error']['Message'],
            )
            raise
    
    def delete_table(self):
        """
            Deletes the table
        """
        
        try:
            self.table.delete()
            self.table = None
        except ClientError as err:
            logger.error(
                "Couldn't delete table because of %s : %s",
                err.response['Error']['Code'],
                err.response['Error']['Message'],
            )
            raise
        
# def run_scenario(table_name, dyn_resource):
#     logging.basicConfig(level=logging.INFO, format = "%(levelname)s : %(message)s")
    
#     print("---" * 50)
#     print("Welcome to the DynamoDB demo")
#     print("---" * 50)
    
#     images = Images(dyn_resource)
#     images_exists = images.exists(table_name)
#     if not images_exists:
#         print(f"\nCreating table {table_name}")
#         images.create_table(table_name)
#         print(f"\nCreated table {images.table_name}")
    
#     @staticmethod
#     def is_float(answer):
#         try:
#             float_answer = float(answer)
#         except ValueError:
#             float_answer = None
#         return float_answer, f"{answer} must be a valid float."


#     my_image = Question.ask_questions(
#         [
#             Question(
#                 'image_name', "Enter the image name: "
#             ),
#             Question(
#                 'image_efs_path', "Enter the s3 path: "
#             ),
#             Question(
#                 'model_prediction_class', 'Enter the model prediction class: '
#             ),
#             Question(
#                 'user_selected_label_boolean', 'Enter the user selected label boolean: '
#             ),
#             Question(
#                 'user_selected_label_answer_choice', 'Enter the user selected answer choice: '
#             ),
#             Question(
#                 'model_confident_score', "Enter the model_confident_score: ", Question.is_float
#             ),
#             Question(
#                 'image_upload_date', "Enter the image upload date: "
#             ),
#         ]
#     )
 
#     my_image['model_confident_score'] = Decimal(str(my_image['model_confident_score']))
#     images.add_image(**my_image)
#     print(f"\nAdded '{my_image['image_name']}' to '{images.table.name}'")
#     print("---"*50)
    

# if __name__ == '__main__':
#     try: 
#         run_scenario(
#             "waste-classification-images-data", boto3.resource('dynamodb', region_name='us-east-1')
#         )
#     except Exception as e:
#         print(f"Something went wrong with demo! Here's what: {e}")