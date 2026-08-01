# A quoi sert cette VM déployée par terraform ?

L'objectif principal est d'accéder régulièrement aux services hébergés sur render afin qu'il restent dans un état "disponible".

Si ces accès réguliers n'étaient pas réalisés, les services s'arrêteraient car le compte render utilisé est en mode 'free', gratuit.  


Le bloc user_data_base64 va post-installer sur la VM  
- passer le timezone à Europe/Paris  
- installer un service de cron  
- créer le script /home/ec2-user/check_urls.sh contenant les URLs à contacter
- mettre à jour la crontab du user ec2-user pour tourner toutes les 10 minutes  
- installer un service apache qui va répondre sur le port 443
- activer un service logrotate réglé pour passer toute les heures et ne conserver que les 10 derniers fichiers cron-url-check.log
- générer un certificat auto-signé pour le serveur apache  

exemple de crontab déployé  
```
[ec2-user@ip-172-31-0-252 ~]$ crontab -l
*/10 * * * * /home/ec2-user/check_urls.sh >> /home/ec2-user/cron-url-check.log 2>&1
```


# Utilisation de terraform pour déployer la VM 

## 1. créer un fichir terraform.tfvars et personnaliser les variables suivantes

```
region = "eu-west-3"  # region a deployer

pathprefix = "/toto/titi/tata/Documents/projetsExterneGithub"

pathsuffix = "mycreds"

key_name = "mykey" # à personnaliser avec le nom de la clé SSH que vous avez créée dans AWS pour accéder à votre instance EC2.

ami_name= "ami-0fa5b605ef6209559" # à personnaliser avc l'ami_id de l'image à utiliser
```

A noter : **pathprefix/pathsuffix** : chemin vers le fichier contenant les credentials aws (aws_access_key_id et aws_secret_access_key) pour accéder à AWS. 
Créer un user spécifique dans IAM.


## 2. étapes terraform pour la construction
se placer dans le repertoire terraformExemples/iac  
```
terraform init
terraform plan
terraform apply -auto-approve

La sortie renvoi l'URL pour aller voir le fichier de log des curl des API dont voici un exemple:  


```

```
Apply complete! Resources: 2 added, 0 changed, 2 destroyed.

Outputs:

cron_log_https_url = "https://ec2-13-36-83-157.eu-west-3.compute.amazonaws.com/cron-log"
```
Note : le certificat étant auto-signé il ya plusieur warning à passer avant d'accéder à la page web.  

## 3. etape terraform pour la suppression de toutes les ressources gérées 
se placer dans le repertoire terraformExemples/iac  
```
terraform destroy
```
