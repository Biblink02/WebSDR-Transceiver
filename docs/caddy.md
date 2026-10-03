# Caddy operations

One Caddy process serves the static Vue/WASM frontend and proxies `/iq` and
`/stream-info` to the stateless backend. The frontend image and Kubernetes
workload are named `websdr-transceiver/frontend` and `frontend`. Proxy Manager,
its admin port and the separate nginx frontend are removed from the manifests.

Edit `config/Caddyfile` for the station's hostname. The existing
`websdr.fbi.h-da.de` address is retained there. The site can be overridden with
`PUBLIC_SITE` in the frontend pod environment for another installation. Browser
`ws_url: /` follows the current origin. Local test environments override
`PUBLIC_SITE` to `localhost` (automatic local CA) or `http://:80` (HTTP only).
The production configuration has no alternate compatibility mode.

For a public hostname, Caddy manages certificates and redirects HTTP to HTTPS.
Point A/AAAA records to the station and forward TCP 80/443. UDP 443 in the new
Kind configuration permits HTTP/3; HTTPS and WebSockets also work over TCP.
Certificates, ACME state and local CA material live in the persistent
`caddy-data` PVC mounted at `/data`. Keep that volume across deployments.
See [automatic HTTPS](https://caddyserver.com/docs/automatic-https) and
[persistent Docker storage](https://caddyserver.com/docs/running#docker-compose).

The image pins official `caddy:2.11.4-alpine`, a published stable tag verified at
implementation time. The newer 2.11.7 Docker tag was not yet published; upstream
2.11.7 documents long-stream regressions in 2.11.6, so that intervening image was
excluded. See [upstream release notes](https://github.com/caddyserver/caddy/releases/tag/v2.11.7).
Update the pinned image deliberately and repeat the HTTPS/WSS check.

`bash deploy.sh` builds and explicitly deploys the application. It removes the
old Proxy Manager/frontend workloads before Caddy binds the public ports. Old
Proxy Manager volumes are not referenced and are preserved for separate backup
or removal; the script does not migrate or erase their stored certificates/data.

To apply only Caddyfile changes to an existing deployment:

```bash
bash scripts/reload-caddy.sh
```

The script validates using the running Caddy version before updating the ConfigMap
and reloading through the pod's loopback admin API. That API is not exposed as a
Service or public port, and there is no browser admin interface or login.
The ConfigMap mounts the entire configuration directory so updates also survive
pod replacement. Reloading may reconnect existing WebSockets; browser retries
and the source idle grace handle brief connection changes. `bash reload.sh`
applies hardware/application settings and restarts the receiver deployments.

Inspect operation without an admin dashboard:

```bash
kubectl --context "kind-${CLUSTER_NAME:-kind}" logs deployment/frontend --tail=100
kubectl --context "kind-${CLUSTER_NAME:-kind}" get pods,pvc
```

Frontend probes use a loopback HTTP endpoint on port 8082, independent of public
DNS, certificate issuance and backend capture. `/iq` is handled before SPA fallback
so WebSocket requests are never rewritten to `index.html`. WASM uses
`application/wasm`; configuration is `no-store`; hashed assets are immutable.

`tests/check-kubernetes.sh` builds the real images in a temporary Kind cluster,
uses `localhost` certificates with their actual trusted root CA, and verifies
HTTPS redirects, WSS beyond 65 seconds, source-only recovery and idle/wake. It
also checks stdin validation/reload and persistent TLS data across frontend pod
replacement. The temporary cluster has a separate kubeconfig and is removed.
Public ACME issuance and RF/device sleep remain production acceptance checks.
