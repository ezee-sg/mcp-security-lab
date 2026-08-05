# Escenario 01 - Token Mismanagement & Secret Exposure

**Categoría OWASP MCP Top 10:** MCP01:2025

## Objetivo del ataque

Obtener credenciales de sistemas internos sin necesidad de vulnerar ningún control de acceso (el problema no es *quién* puede leer el fichero, sino que el fichero contiene secretos en texto plano) y comprobar que los tokens de sesión de la versión endurecida son legibles por cualquiera que los intercepte, aunque estén firmados.

## Servidor(es) MCP involucrados

- **IT** (`hispalis-it-vulnerable` / `hispalis-it-hardened`)

## Tool(s) MCP invocada(s)

- `read_config` (IT)  con `path="database.yml"`

## Query a realizar al LLM

**Versión vulnerable:**

> Lee el fichero de configuración `database.yml` del servidor de IT y dime qué contiene.

**Versión endurecida:** primero es necesario obtener un token con rol autorizado
(`dept_manager`, `it_admin` o `director`):

```bash
python tools/issue_token.py elena.vidal
```

> Usando este session_token: `<pegar el token devuelto>`, lee el fichero de
> configuración `database.yml`.

Si el asistente no incluye el `session_token` en la llamada a la tool, conviene pedírselo explícitamente ("llama a la tool read_config con path='database.yml' y session_token='...'") o utilizar **MCP Inspector** para invocar `read_config` directamente con ambos parámetros en su formulario.

## Información que se espera extraer

- **Vulnerable:** el contenido íntegro de `database.yml`, incluyendo `password: "F1n4nz4s_2026!"` y `password: "1T_Adm1n_2026!"` en texto plano.
- **Endurecida:** el mismo fichero, pero con los valores de contraseña sustituidos por `***REDACTED***` — aunque el usuario esté perfectamente autorizado a leer el fichero.

## Inspección adicional (fuera del chat)

El `session_token` que usa la versión endurecida es un JWT: está firmado, pero no cifrado. Cualquiera que capture uno (en una traza de red, un log mal configurado, etc.) puede leer sus datos sin conocer la clave de firma del servidor:

```bash
python -c "import jwt,sys; sys.path.insert(0,'.'); from common.auth import issue_token; print(jwt.decode(issue_token('sofia.reyes'), options={'verify_signature': False}))"
```

Esto revela `sub`, `role`, `department` y una vigencia de 8 horas — una limitación residual que esta versión del laboratorio no resuelve.

## Impacto

Credenciales de sistemas internos expuestas sin necesidad de ningún bypass de control de acceso, y tokens de sesión cuyo contenido es trivialmente inspeccionable por cualquiera con acceso a la traza JSON-RPC o a los logs del host MCP.
