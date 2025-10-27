Architettura Kubernetes per sessioni utente con websocketd (broker) e Operator kopf

Contenuto del repository
- k8s/crd/usersession-crd.yaml: definizione della CustomResourceDefinition (CRD) UserSession.
- broker/gestore-sessione.sh: script sorgente avviato da websocketd che crea/elimina la UserSession.
- operator/main.py: Codice sorgente dell'Operator.
- operator/requirements.txt: dipendenze Python dell'Operator.
- k8s/broker.yaml: Namespace, ServiceAccount, RBAC e Deployment del broker.
- k8s/operator.yaml: Namespace, ServiceAccount, RBAC e Deployment dell'Operator.
- scripts/create-configmaps.sh: Script che crea ConfigMaps dai file sorgente.
- scripts/deploy.sh: Script di deployment completo.

Prerequisiti
- Cluster Kubernetes 1.24+ con permessi cluster-admin per l'installazione iniziale.
- kubectl configurato verso il cluster.
- Accesso a Docker Hub dal cluster (per tirare le immagini pubbliche).

Installazione

Metodo 1 - Script automatico (consigliato):
  scripts/deploy.sh

Metodo 2 - Manuale:
1) Applica la CRD UserSession
   kubectl apply -f k8s/crd/usersession-crd.yaml

2) Crea i ConfigMaps dai file sorgente
   scripts/create-configmaps.sh

3) Applica i manifest dell'Operator
   kubectl apply -f k8s/operator.yaml

4) Applica i manifest del Broker
   kubectl apply -f k8s/broker.yaml

Non è richiesto alcun build/push di immagini: i manifest usano immagini preesistenti da Docker Hub (python:3.11-slim, bitnami/kubectl, alpine).

Note sul Broker
- Il Deployment del broker espone websocketd sulla porta 8080 all’interno del Pod. Aggiungi un Service/Ingress se vuoi esporlo esternamente.
- Lo script gestore-sessione.sh genera un nome univoco per la UserSession e crea la CR a livello cluster. Quando la connessione websocket si chiude, un trap elimina la CR.

Note sull’Operator
- L’Operator osserva le UserSession (cluster-scoped). Alla creazione di una UserSession chiamata <nome>, crea:
  - Namespace <nome>
  - ResourceQuota di esempio (1 Pod, 0.5 vCPU richieste/1 vCPU limiti, 512Mi richieste/1Gi limiti)
  - NetworkPolicy default-deny (Ingress/Egress), per isolamento completo
  - Pod worker busybox nel namespace della sessione
- Alla cancellazione della UserSession, l’Operator elimina tutto l’ambiente eliminando il Namespace corrispondente.

Personalizzazioni
- Modifica l’immagine del Pod worker in operator/main.py (ensure_worker_pod) secondo le tue esigenze applicative.
- Adatta la ResourceQuota nel medesimo file.
- Aggiungi Service/Ingress per il broker in k8s/broker.yaml se necessario.

Pulizia
- Per rimuovere tutto:
  kubectl delete -f k8s/broker.yaml
  kubectl delete -f k8s/operator.yaml
  kubectl delete -f k8s/crd/usersession-crd.yaml

Test con kind (E2E)
- Requisiti: Docker, kind, kubectl.
- Esegui il test end-to-end automatico che crea un cluster kind, applica CRD/Operator/Broker, crea una UserSession e verifica la pulizia:
  scripts/kind-e2e.sh
- Variabili opzionali:
  CLUSTER_NAME=usersess KIND_NODE_IMAGE=kindest/node:v1.30.0 KEEP_CLUSTER=1 scripts/kind-e2e.sh
  (KEEP_CLUSTER=1 mantiene il cluster per ispezioni.)
- In alternativa, test manuale via websocketd:
  kubectl -n websocket-broker port-forward deploy/websocket-broker 8080:8080
  npx wscat -c ws://127.0.0.1:8080
  # chiudi la connessione per far eliminare la CR

Note sui ConfigMaps
- I ConfigMaps per i file sorgente (operator/main.py e broker/gestore-sessione.sh) vengono creati dinamicamente dagli script.
- Per aggiornare il codice: modifica i file sorgente e ri-esegui create-configmaps.sh.
- Questo mantiene i file sorgente separati dalle configurazioni Kubernetes per maggiore chiarezza.

Sicurezza e RBAC
- Il broker ha un ClusterRole con permessi limitati a creare ed eliminare solo la risorsa usersessions.sessions.example.com.
- L’Operator ha un ClusterRole con permessi cluster per gestire Namespaces, Pods, ResourceQuotas e NetworkPolicies, oltre a leggere/patchare lo stato delle UserSession.

Debug
- Log dell’Operator:
  kubectl -n usersession-operator logs deploy/usersession-operator -f
- Log del broker:
  kubectl -n websocket-broker logs deploy/websocket-broker -f

Licenza
- Esempio didattico. Adattare a produzione con cura (quote, limiti, politiche di rete, autenticazione, auditing).