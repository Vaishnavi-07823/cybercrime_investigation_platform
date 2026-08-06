# Infrastructure Notes

The root `docker-compose.yml` is the supported local-development deployment.

For production, create separate environment overlays or Kubernetes manifests with:

- TLS certificates and private service networking
- Secrets supplied from a secrets manager
- Persistent-volume encryption and backup policies
- OpenSearch security enabled
- MinIO/S3 object lock and retention
- PostgreSQL high availability and point-in-time recovery
- Neo4j backup and recovery procedures
- Resource requests, limits and autoscaling
- NetworkPolicies and workload identities
- Signed images and admission controls
- Centralized append-only audit export

Do not promote the development Compose file directly to an internet-facing environment.
