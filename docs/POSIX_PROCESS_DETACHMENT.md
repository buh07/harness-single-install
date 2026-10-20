# POSIX monitor and helper lifetime

The native `spawn_detached` helper starts POSIX children in a new session and
process group. A monitor, lane controller, or optional public-check service must
remain alive after its successful setup or launch command returns; otherwise
terminal hangup or command-runner process-group cleanup can silently stop it.
Redirecting standard streams alone does not detach its process group.

Windows retains its existing no-window creation flag and virtual-environment
interpreter handling; `start_new_session` is false there. Provider launches
already use a separate POSIX session and are unchanged. Usage collectors use
that provider boundary, not this helper.

This is native process creation, not a wrapper, daemon supervisor, restart loop,
or permission bypass. Every service still records its exact PID and creation
identity, readiness is still required, and cleanup still uses the native
identity-bound stop/shutdown paths. Unsupported process observations remain
unproven. A new session does not evade host-wide or container-wide process
cleanup, and it is not proof that a provider or real model turn works.

Focused regressions cover native POSIX session/group separation, refusal to
terminate without a creation identity, exact-identity cleanup, and unchanged
Windows spawn options. Live startup validation must also observe the exact
ready monitor from a separate operator command after setup returns, not only
while setup and preparation share one long-lived parent process.
