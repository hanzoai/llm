{{/*
Expand the name of the chart.
*/}}
{{- define "llm.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "llm.fullname" -}}
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
{{- define "llm.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "llm.labels" -}}
helm.sh/chart: {{ include "llm.chart" . }}
{{ include "llm.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "llm.selectorLabels" -}}
app.kubernetes.io/name: {{ include "llm.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "llm.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "llm.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Get redis service name
*/}}
{{- define "llm.redis.serviceName" -}}
{{- if and (eq .Values.redis.architecture "standalone") .Values.redis.sentinel.enabled -}}
{{- printf "%s-%s" .Release.Name (default "redis" .Values.redis.nameOverride | trunc 63 | trimSuffix "-") -}}
{{- else -}}
{{- printf "%s-%s-master" .Release.Name (default "redis" .Values.redis.nameOverride | trunc 63 | trimSuffix "-") -}}
{{- end -}}
{{- end -}}

{{/*
Get redis service port
*/}}
{{- define "llm.redis.port" -}}
{{- if .Values.redis.sentinel.enabled -}}
{{ .Values.redis.sentinel.service.ports.sentinel }}
{{- else -}}
{{ .Values.redis.master.service.ports.redis }}
{{- end -}}
{{- end -}}
