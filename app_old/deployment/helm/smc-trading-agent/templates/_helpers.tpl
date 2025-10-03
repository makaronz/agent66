{{/*
Expand the name of the chart.
*/}}
{{- define "smc-trading-agent.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "smc-trading-agent.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "smc-trading-agent.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "smc-trading-agent.labels" -}}
helm.sh/chart: {{ include "smc-trading-agent.chart" . }}
{{ include "smc-trading-agent.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: trading-agent
app.kubernetes.io/part-of: smc-trading-platform
{{- end }}

{{/*
Selector labels
*/}}
{{- define "smc-trading-agent.selectorLabels" -}}
app.kubernetes.io/name: {{ include "smc-trading-agent.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "smc-trading-agent.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "smc-trading-agent.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the namespace name
*/}}
{{- define "smc-trading-agent.namespace" -}}
{{- if .Values.namespace.create }}
{{- .Values.namespace.name | default .Release.Namespace }}
{{- else }}
{{- .Release.Namespace }}
{{- end }}
{{- end }}

{{/*
Generate the image name
*/}}
{{- define "smc-trading-agent.image" -}}
{{- $registry := .Values.global.imageRegistry | default .Values.image.registry -}}
{{- $repository := .Values.image.repository -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repository $tag -}}
{{- else -}}
{{- printf "%s:%s" $repository $tag -}}
{{- end -}}
{{- end }}

{{/*
Generate storage class name
*/}}
{{- define "smc-trading-agent.storageClass" -}}
{{- $storageClass := .Values.global.storageClass | default .storageClass -}}
{{- if $storageClass -}}
{{- printf "%s" $storageClass -}}
{{- end -}}
{{- end }}

{{/*
Generate pull secrets
*/}}
{{- define "smc-trading-agent.imagePullSecrets" -}}
{{- $pullSecrets := .Values.global.imagePullSecrets | default .Values.image.pullSecrets -}}
{{- if $pullSecrets -}}
{{- range $pullSecrets }}
- name: {{ . }}
{{- end }}
{{- end -}}
{{- end }}