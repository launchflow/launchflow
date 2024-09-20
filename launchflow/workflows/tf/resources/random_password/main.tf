resource "random_password" "password" {
  length = var.length
}

output "password" {
  value     = random_password.password.result
  sensitive = true
}
