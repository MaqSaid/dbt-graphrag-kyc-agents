module "networking" {
  source = "./modules/networking"

  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
  aws_region   = var.aws_region
}

module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
}

module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
}

module "neptune" {
  source = "./modules/neptune"

  project_name         = var.project_name
  environment          = var.environment
  instance_class       = var.neptune_instance_class
  subnet_ids           = module.networking.private_subnet_ids
  security_group_id    = module.networking.neptune_security_group_id
}

module "ecs" {
  source = "./modules/ecs"

  project_name      = var.project_name
  environment       = var.environment
  container_image   = var.container_image
  task_cpu          = var.ecs_task_cpu
  task_memory       = var.ecs_task_memory
  min_tasks         = var.ecs_min_tasks
  max_tasks         = var.ecs_max_tasks
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.ecs_security_group_id
  target_group_arn  = module.networking.target_group_arn
  execution_role_arn = module.iam.ecs_execution_role_arn
  task_role_arn     = module.iam.ecs_task_role_arn
}
