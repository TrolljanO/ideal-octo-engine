import boto3
import logging
import os

# Configuração de logging
app = type('app', (object,), {'logger': logging.getLogger('app')})
logging.basicConfig(level=logging.INFO)

def start_processing_server(instance_id):
    try:
        # Cliente EC2 usando credenciais explicitamente
        ec2_client = boto3.client(
            'ec2',
            region_name='us-east-2',
            aws_access_key_id='AKIA3FLDYRAWHFINNFXC',
            aws_secret_access_key='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'
        )

        response = ec2_client.start_instances(InstanceIds=[instance_id])
        app.logger.info(f"Iniciando a instância: {instance_id}")
        return True
    except Exception as e:
        app.logger.error(f"Erro ao iniciar o servidor de processamento: {e}")
        return False

# ID da instância EC2
instance_id = 'i-0a375ebcd52f5a02d'

# Iniciar a instância EC2
success = start_processing_server(instance_id)

if success:
    print(f"Instância {instance_id} iniciada com sucesso!")
else:
    print(f"Falha ao iniciar a instância {instance_id}.")
