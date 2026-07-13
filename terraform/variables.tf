variable "project_name" {
  description = "Name of the project for resource tagging"
  type        = string
  default     = "kyc-pipeline"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "ecs_task_cpu" {
  description = "CPU units for ECS Fargate task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "ecs_task_memory" {
  description = "Memory (MiB) for ECS Fargate task"
  type        = number
  default     = 2048
}

variable "ecs_min_tasks" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 2
}

variable "ecs_max_tasks" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 10
}

variable "neptune_instance_class" {
  description = "Neptune instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "container_image" {
  description = "Docker container image for the KYC pipeline"
  type        = string
  default     = "kyc-pipeline:latest"
}

variable "neptune_password" {
  description = "Neptune database password"
  type        = string
  sensitive   = true
  default     = ""
}
