import os
import time
import hashlib

# Diretório do projeto
project_dir = 'C:\\Users\\T_J\\Documents\\LIMPAPASTA.COM'

# Arquivo de log
log_file = 'changes.log'


# Função para calcular o hash do conteúdo de um arquivo
def hash_file(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


# Função para mapear arquivos e calcular hashes
def map_files(directory):
    file_map = {}
    for root, dirs, files in os.walk(directory):
        for name in files:
            filepath = os.path.join(root, name)
            file_map[filepath] = hash_file(filepath)
    return file_map


# Carregar o estado inicial dos arquivos
prev_state = map_files(project_dir)

# Monitorar alterações
while True:
    time.sleep(10)  # Verifica a cada 10 segundos
    current_state = map_files(project_dir)

    # Verificar por novos arquivos ou alterações
    with open(log_file, 'a') as log:
        for filepath, hash_val in current_state.items():
            if filepath not in prev_state:
                log.write(f'[NEW] {filepath} - {time.ctime()}\n')
            elif prev_state[filepath] != hash_val:
                log.write(f'[MODIFIED] {filepath} - {time.ctime()}\n')

        # Verificar arquivos deletados
        for filepath in prev_state:
            if filepath not in current_state:
                log.write(f'[DELETED] {filepath} - {time.ctime()}\n')

    # Atualizar o estado anterior
    prev_state = current_state
