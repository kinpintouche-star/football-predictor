# Front Football Predictor

API de prediction construite avec FastAPI

## .env

En local, créer `foot-predictapi/.env` :

```txt
export MODEL_ID="m-91ffd862a5564e5aa065f68f3e45bf3d"
export NEON_DATABASE_URL=postgresxxxxxx
export AWS_ACCESS_KEY_ID="zzzzzzzzzzzzz
export AWS_SECRET_ACCESS_KEY="zzzzzzzzzzzzzzzzz"
export ARTIFACT_ROOT="s3://xxxxxxxxxxxxx-mlflow"
export APP_URI="https://zzzzzzzzzzzzzzz.hf.space"
export PORT_INFERENCE_API=4120
```

## Lancer en local

Lancer d'abord l'API, puis :

```bash
cd foot-predictapi
/usr/local/bin/python3.13 -m venv my-super-venv
source my-super-venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py  # soir si streamlit dev app.py fonctionne 
```

## Docker
### build en local de l'image docker foot-predictapi:0.1.1
se placer dans le sous-repertoire foot-predictapi

```
source .env
docker build -t foot-predictapi:0.1.1 .
```

### démarrer en  local un container utilisant l'image foot-predictapi:0.1.1
puis lancer le container en local  

```
source .env
docker run --rm -it \
-e APP_URI=$APP_URI \
-e MODEL_ID=$MODEL_ID \
-e NEON_DATABASE_URL=$NEON_DATABASE_URL \
-e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
-e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
-e ARTIFACT_ROOT=$ARTIFACT_ROOT \
-e PORT_INFERENCE_API=$PORT_INFERENCE_API \
-p $PORT_INFERENCE_API:$PORT_INFERENCE_API \
foot-predictapi:0.1.1
```

### controle de l'état l'api
controle de l'accès sur le port 4120 (qui peut être changé avec la variable PORT_INFERENCE_API du .env )  
depuis un browser web local:  http://localhost:4120/docs ou 
curl http://localhost:4120/docs en CLI