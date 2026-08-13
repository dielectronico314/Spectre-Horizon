/**
 * background.js — Efectos visuales puros (sin contacto con backend)
 * - Animación de fondo atada a waterfall real
 * - Pulso de estado desde heartbeat real
 * - Skeletons para cargas de 3D y reportes
 * - Lucide icons replacement
 * - Línea de tiempo (commit graph style)
 * - Dial de frecuencias
 * - Contadores animados
 * - Paleta de comandos (Cmd+K)
 * - Atajos de navegación (g+e, g+s)
 * - Toasts de confirmación
 */

// ============ LED DE ESTADO — 3 ESTADOS EN VIVO (PASO 4) ============
// Render inicial: server-side desde status.sensor_conectado (Jinja2, ver estado.html).
// Después de cargar, se sondea /api/v1/sensor/health (ya arreglado — antes daba 500)
// cada 10s para detectar desconexión/reconexión real del hardware sin recargar la página.

function _clasificarSaludSensor(data) {
    if (data && data.status === 'success') return 'connected';
    if (data && data.error_state === 'Sensor no conectado') return 'disconnected';
    // Cualquier otro error (ocupado, calfile, permisos, driver ausente, timeout, etc.)
    // significa que hay algo que revisar, pero no es necesariamente un cable desconectado.
    return 'warning';
}

const _ETIQUETAS_ESTADO_SENSOR = {
    connected: 'Sensor conectado',
    disconnected: 'Sensor desconectado',
    warning: 'Revisar conexión del sensor',
};

function _renderMainStatusBar(estado, detalle) {
    if (estado === 'connected') {
        return `<div class="status-bar" style="background-color: var(--success); color: #000;">
            <span class="status-label"><i data-lucide="circle-dot" style="color: var(--sev-low); vertical-align: -3px;"></i> Sensor Conectado y Listo</span>
            <span>(Hardware OK)</span>
        </div>`;
    }
    if (estado === 'disconnected') {
        return `<div class="status-bar error">
            <span class="status-label"><i data-lucide="alert-circle" style="color: var(--sev-high); vertical-align: -3px;"></i> ALERTA: Sensor Desconectado</span>
            <span>Verifique la conexión USB o la alimentación.</span>
        </div>`;
    }
    // warning
    return `<div class="status-bar warning">
        <span class="status-label"><i data-lucide="triangle-alert" style="color: var(--sev-medium); vertical-align: -3px;"></i> Revisar Sensor</span>
        <span>${detalle ? detalle.replace(/</g, '&lt;') : 'Hay un problema con el hardware, ver detalle.'}</span>
    </div>`;
}

async function pollSensorLed() {
    const led = document.getElementById('sensor-led');
    const label = document.getElementById('sensor-status-label');
    const statusBar = document.getElementById('main-status-bar');
    if (!led) return;

    let estado = 'warning';
    let detalle = null;
    try {
        const res = await fetch('/api/v1/sensor/health');
        const data = await res.json();
        estado = _clasificarSaludSensor(data);
        detalle = data.message || data.error_state;
    } catch (err) {
        estado = 'warning';
        detalle = 'Sin respuesta del servidor API';
    }

    const previo = led.getAttribute('data-state');
    led.setAttribute('data-state', estado);
    if (label) label.textContent = _ETIQUETAS_ESTADO_SENSOR[estado];
    if (detalle) led.title = detalle;

    // Solo tocar el DOM de la barra grande si el estado realmente cambió — evita
    // parpadeos y pérdida de foco en cada poll cuando no hay novedad.
    if (statusBar && previo !== estado) {
        statusBar.innerHTML = _renderMainStatusBar(estado, detalle);
        if (window.lucideReplace) window.lucideReplace();
    }

    // Avisar con un toast solo cuando el estado realmente cambia (no en cada poll)
    if (previo && previo !== estado && window.showToast) {
        const tipo = estado === 'connected' ? 'success' : (estado === 'disconnected' ? 'error' : 'warning');
        window.showToast(_ETIQUETAS_ESTADO_SENSOR[estado], tipo);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    pollSensorLed();
    // 15s: por encima del timeout de 10s del subprocess de sondeo (ver app/api/main.py),
    // para evitar que los polls se encimen si el sondeo tarda el máximo.
    setInterval(pollSensorLed, 15000);
});

// ============ SKELETONS PARA CARGAS (PASO 5) ============
// Mostrar skeleton mientras fetch() está pendiente

window.showLoadingSkeleton = function(element) {
    if (!element) return;
    element.classList.add('skeleton');
    element.style.minHeight = '200px';
};

window.hideLoadingSkeleton = function(element) {
    if (!element) return;
    element.classList.remove('skeleton');
};

// Para toggle 3D/2D en estado.html
const waterfallToggle = document.getElementById('waterfall-toggle');
const waterfallContainer = document.getElementById('waterfall-container');

if (waterfallToggle && waterfallContainer) {
    waterfallToggle.addEventListener('change', async (e) => {
        const is3d = e.target.checked;
        const sessionId = waterfallContainer.dataset.sessionId;

        if (!sessionId) return;

        // Mostrar skeleton mientras carga
        window.showLoadingSkeleton(waterfallContainer);

        try {
            const endpoint = is3d
                ? `/api/v1/sessions/${sessionId}/waterfall3d.json`
                : `/api/v1/sessions/${sessionId}/waterfall`;

            const response = await fetch(endpoint);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            // Aquí iría la lógica de renderizado (Plotly para 3D, canvas para 2D)
            // Por ahora, solo removemos el skeleton
            window.hideLoadingSkeleton(waterfallContainer);
        } catch (err) {
            console.error('Waterfall load error:', err);
            window.hideLoadingSkeleton(waterfallContainer);
        }
    });
}

// ============ LUCIDE ICONS REPLACEMENT (PASO 6) ============
// Reemplazar emojis genéricos con iconos SVG consistentes

window.lucideReplace = function() {
    if (window.lucide) {
        lucide.createIcons();
    }
};

// Ejecutar al cargar y después de navegación dinámicas
document.addEventListener('DOMContentLoaded', lucideReplace);

// ============ FONDO ANIMADO (PASO 2) ============
// Inyectar URL de waterfall más reciente — SOLO si la imagen existe de verdad

window.setBackgroundWaterfall = function(waterfallUrl) {
    if (!waterfallUrl) return;

    // Verificar que la imagen existe antes de aplicarla
    const img = new Image();
    img.onload = function() {
        // Solo si la imagen cargó, inyectar y activar animación
        document.documentElement.style.setProperty('--bg-waterfall-url', `url('${waterfallUrl}')`);
        document.body.classList.add('has-waterfall');
    };
    img.onerror = function() {
        // Si no existe, mantener fondo sólido
        console.warn(`Waterfall no disponible: ${waterfallUrl}`);
    };
    img.src = waterfallUrl;
};

// Llamada desde estado.html: {% if ultima_sesion and ultima_sesion.waterfall_2d_url %}
// <script>window.setBackgroundWaterfall('{{ ultima_sesion.waterfall_2d_url }}');</script>

// ============ GAUGE RADIAL (PASO 4) ============
// Renderizar gauges de confianza en evento_detalle.html

window.initConfidenceGauges = function() {
    document.querySelectorAll('.confidence-gauge').forEach(svg => {
        const confidence = parseFloat(svg.getAttribute('data-confidence')) || 0;
        const dashValue = confidence * 100;
        const circle = svg.querySelector('.gauge-fill');
        if (circle) {
            circle.setAttribute('stroke-dasharray', `${dashValue} 100`);
        }
    });
};

// ============ CONTADOR ANIMADO (PASO 3) ============
// Cuenta desde 0 hasta el número final en ~800ms

window.countUp = function(el, target, duration = 800) {
    if (!el) return;
    const start = performance.now();
    function tick(now) {
        const p = Math.min((now - start) / duration, 1);
        el.textContent = Math.floor(p * target);
        if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
};

// Ejecutar efectos visuales al cargar
document.addEventListener('DOMContentLoaded', function() {
    // Gauges
    window.initConfidenceGauges();

    // Contadores
    const contadorEventos = document.getElementById('counter-eventos');
    const contadorSesiones = document.getElementById('counter-sesiones');

    if (contadorEventos) {
        const targetEventos = parseInt(contadorEventos.textContent) || 0;
        window.countUp(contadorEventos, targetEventos, 800);
    }

    if (contadorSesiones) {
        const targetSesiones = parseInt(contadorSesiones.textContent) || 0;
        window.countUp(contadorSesiones, targetSesiones, 800);
    }
});

// ============ LÍNEA DE TIEMPO (PASO 1) ============
// Commit graph style timeline con color por severidad

window.initTimeline = function() {
    const timelineCells = document.querySelectorAll('.timeline-dot');
    if (timelineCells.length === 0) return;

    // Fetch todos los eventos para colorear por severidad máxima real
    fetch('/api/v1/events')
        .then(r => r.json())
        .then(events => {
            const rango = { ninguna: 0, low: 1, medium: 2, high: 3 };
            const severidadMaxPorSesion = {};

            events.forEach(e => {
                const sid = e.session_id;
                const sev = e.severidad || 'low';
                const actual = severidadMaxPorSesion[sid] || 'ninguna';
                if (rango[sev] > rango[actual]) {
                    severidadMaxPorSesion[sid] = sev;
                }
            });

            // Aplicar data-sev por session_id real, no por índice de array
            timelineCells.forEach(cell => {
                const sessionId = cell.getAttribute('data-session-id');
                const sev = severidadMaxPorSesion[sessionId] || 'ninguna';
                cell.setAttribute('data-sev', sev);
            });
        })
        .catch(err => console.warn('Timeline: eventos no disponibles', err));
};

document.addEventListener('DOMContentLoaded', initTimeline);

// ============ DIAL DE FRECUENCIAS (PASO 2) ============

window.initFrequencyDial = function() {
    const dialContainer = document.getElementById('frequency-dial-container');
    if (!dialContainer) return;

    fetch('/api/v1/sessions')
        .then(r => r.json())
        .then(sessions => {
            // Extraer frecuencias únicas
            const freqs = {};
            sessions.forEach(s => {
                if (s.fc_hz) {
                    const mhz = Math.round(s.fc_hz / 1e6);
                    freqs[mhz] = (freqs[mhz] || 0) + 1;
                }
            });

            const sortedFreqs = Object.keys(freqs).map(f => parseInt(f)).sort((a, b) => a - b);

            // Renderizar ticks
            dialContainer.innerHTML = '';
            sortedFreqs.forEach(freq => {
                const tick = document.createElement('div');
                tick.className = 'frequency-tick';
                tick.innerHTML = `
                    <div class="frequency-tick-dot"></div>
                    <div class="frequency-tick-label">${freq} MHz</div>
                `;
                tick.addEventListener('click', () => {
                    // Navegar a eventos de esa frecuencia
                    window.location.href = `/dashboard/eventos?frecuencia_mhz=${freq}`;
                });
                dialContainer.appendChild(tick);
            });
        })
        .catch(err => console.warn('Frequency dial: error', err));
};

document.addEventListener('DOMContentLoaded', initFrequencyDial);

// ============ TOAST NOTIFICATIONS (PASO 7) ============

window.showToast = function(message, type = 'success', duration = 3000) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, duration);
};

// ============ PALETA DE COMANDOS (PASO 5) ============

const commandPalette = {
    isOpen: false,
    commands: [
        { title: 'Ir a Eventos', hint: 'Ver tabla de eventos', action: () => window.location.href = '/dashboard/eventos' },
        { title: 'Ir a Sesiones', hint: 'Explorador de capturas', action: () => window.location.href = '/dashboard/sesiones' },
        { title: 'Actualizar Estado', hint: 'Recargar página', action: () => window.location.reload() },
        { title: 'Buscar Eventos...', hint: 'Abrir filtros avanzados', action: () => window.location.href = '/dashboard/eventos' },
    ],

    open() {
        if (this.isOpen) return;
        this.isOpen = true;
        this.render();
    },

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;
        const palette = document.getElementById('command-palette');
        if (palette) palette.classList.remove('open');
    },

    render() {
        let palette = document.getElementById('command-palette');
        if (!palette) {
            palette = document.createElement('div');
            palette.id = 'command-palette';
            palette.className = 'command-palette';
            palette.innerHTML = `
                <div class="command-palette-content">
                    <div class="command-palette-input">
                        <input type="text" id="command-input" placeholder="Buscar comando..." autofocus>
                    </div>
                    <div class="command-palette-results" id="command-results"></div>
                </div>
            `;
            document.body.appendChild(palette);

            const input = document.getElementById('command-input');
            input.addEventListener('input', (e) => this.filter(e.target.value));
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') this.close();
                if (e.key === 'Enter') this.executeSelected();
            });

            palette.addEventListener('click', (e) => {
                if (e.target === palette) this.close();
            });
        }

        palette.classList.add('open');
        document.getElementById('command-input').focus();
        this.renderResults(this.commands);
    },

    filter(query) {
        const filtered = this.commands.filter(c => c.title.toLowerCase().includes(query.toLowerCase()));
        this.renderResults(filtered);
    },

    renderResults(results) {
        const resultsDiv = document.getElementById('command-results');
        resultsDiv.innerHTML = results.map((cmd, idx) => `
            <div class="command-item" data-index="${idx}">
                <div class="command-item-title">${cmd.title}</div>
                <div class="command-item-hint">${cmd.hint}</div>
            </div>
        `).join('');

        resultsDiv.querySelectorAll('.command-item').forEach((item, idx) => {
            if (idx === 0) item.classList.add('selected');
            item.addEventListener('click', () => {
                this.commands.find(c => c.title === item.querySelector('.command-item-title').textContent)?.action();
                this.close();
            });
        });
    },

    executeSelected() {
        const selected = document.querySelector('.command-item.selected');
        if (selected) selected.click();
    }
};

// Atajo Cmd+K / Ctrl+K
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        commandPalette.open();
    }
    if (e.key === 'Escape') commandPalette.close();
});

// ============ ATAJOS GITHUB-STYLE (PASO 6) ============
// g + e → eventos, g + s → sesiones

let lastKeyWasG = false;
document.addEventListener('keydown', (e) => {
    // Solo si no estamos en un input
    if (e.target.tagName.toLowerCase() === 'input') return;

    if (e.key === 'g') {
        lastKeyWasG = true;
        window.showToast('g + e → eventos | g + s → sesiones', 'success', 2000);
        setTimeout(() => { lastKeyWasG = false; }, 2000);
    } else if (lastKeyWasG) {
        lastKeyWasG = false;
        if (e.key === 'e') window.location.href = '/dashboard/eventos';
        if (e.key === 's') window.location.href = '/dashboard/sesiones';
    }
});

// ============ LOG-TAIL EN VIVO (SECCIÓN 9) ============

window.actualizarLogTail = function() {
    const container = document.getElementById('log-tail-container');
    if (!container) return;

    fetch('/api/v1/system/log-tail?lines=20')
        .then(r => r.json())
        .then(data => {
            if (!data.available) {
                container.innerHTML = '<div class="log-line error">Log no disponible</div>';
                return;
            }
            container.innerHTML = data.lines.map(line => {
                // Colorear por severidad (error, warning, info)
                let cls = 'log-line';
                if (line.includes('ERROR') || line.includes('error') || line.includes('Exception')) cls += ' error';
                else if (line.includes('WARN') || line.includes('warning')) cls += ' warning';
                else if (line.includes('INFO') || line.includes('info')) cls += ' info';
                return `<div class="${cls}">${line.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>`;
            }).join('');
        })
        .catch(err => {
            container.innerHTML = '<div class="log-line error">Error cargando log: ' + err.message + '</div>';
        });
};

document.addEventListener('DOMContentLoaded', function() {
    window.actualizarLogTail();
    setInterval(window.actualizarLogTail, 5000);
});
