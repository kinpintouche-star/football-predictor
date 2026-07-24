import mlflow
import pandas as pd
from sklearn.metrics import accuracy_score
import os
from pathlib import Path
import getpass
from dotenv import load_dotenv

# Load a repo-level .env when present (handy for local dev and batch runs).
for parent in [Path.cwd(), *Path.cwd().parents]:
    env_file = parent / ".env"
    if env_file.is_file():
        load_dotenv(env_file,override=True)
        break

X_test = pd.read_csv('X_test_dataset.csv', sep=';', encoding='utf-8')
y_test = pd.read_csv('y_test_dataset.csv', sep=';', encoding='utf-8').squeeze()
y_already_predicted = pd.read_csv('y_test_predicted_dataset.csv', sep=';', encoding='utf-8').squeeze()



# Set tracking URI to your Hugging Face application
mlflow.set_tracking_uri(os.environ["APP_URI"])
model_id = os.environ["MODEL_ID"]
model = mlflow.sklearn.load_model(f"models:/{model_id}")

y_pred=model.predict(X_test)
print(y_pred)

accuracy = accuracy_score(y_test, y_pred)
print(accuracy)

print()
print(f"check y_pred before and after model downloading")
print((y_already_predicted == y_pred).value_counts())