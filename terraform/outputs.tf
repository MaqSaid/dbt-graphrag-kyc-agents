output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = module.ecs.cluster_arn
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.ecs.service_name
}

output "neptune_endpoint" {
  description = "Neptune cluster endpoint"
  value       = module.neptune.cluster_endpoint
}

output "neptune_reader_endpoint" {
  description = "Neptune cluster reader endpoint"
  value       = module.neptune.reader_endpoint
}

output "s3_raw_bucket" {
  description = "S3 bucket for raw data staging"
  value       = module.s3.raw_bucket_name
}

output "s3_audit_bucket" {
  description = "S3 bucket for audit logs"
  value       = module.s3.audit_bucket_name
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.networking.alb_dns_name
}
