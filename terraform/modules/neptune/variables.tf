variable "project_name" { type = string }
variable "environment" { type = string }
variable "instance_class" { type = string }
variable "subnet_ids" { type = list(string) }
variable "security_group_id" { type = string }
