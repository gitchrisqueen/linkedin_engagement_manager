from cqc_lem import assets_dir

# app path starts from src folder portion of the assets_dir and appends 'app/' to the beginning
CONTAINER_APP_ASSETS_PATH = 'app/'+assets_dir.split('src')[1]
EFS_VOLUME_NAME = 'cqc-lem-ecs-efs-volume'