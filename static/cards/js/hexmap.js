/**
 * Hex map click handling hook.
 *
 * Uses data-col and data-row attributes on SVG <g> elements
 * to detect which hex was clicked, then pushes a set_hex event.
 * Also handles Esc key to close hex note popups and timeline
 * entry hover to highlight locations on the map.
 */

window.Hooks = window.Hooks || {};

window.Hooks.HexMap = {
    mounted() {
        this._bindClick();
        this._bindKeydown();
        this._bindTimelineHover();
        this._bindHighlightSignal();
    },
    updated() {
        this._bindClick();
        this._bindTimelineHover();
    },
    destroyed() {
        if (this._keyHandler) {
            document.removeEventListener('keydown', this._keyHandler);
        }
        if (this._hoverCleanup) {
            this._hoverCleanup();
        }
        if (this._signalTimer) {
            clearTimeout(this._signalTimer);
        }
    },
    _bindHighlightSignal() {
        var hook = this;
        // Server pushes 'hex_highlight' to every player when the keeper
        // highlights a hex. Draw a transient pulsing signal on the map.
        this.handleEvent('hex_highlight', function(payload) {
            var svg = hook.el.querySelector('svg');
            if (!svg || payload == null) return;
            var cx = payload.cx, cy = payload.cy, r = payload.r;
            if (cx == null || cy == null || r == null) return;

            // Remove any previous signal still on the map
            var prev = svg.querySelector('.hex-signal');
            if (prev) prev.remove();
            if (hook._signalTimer) clearTimeout(hook._signalTimer);

            var SVGNS = 'http://www.w3.org/2000/svg';
            var g = document.createElementNS(SVGNS, 'g');
            g.setAttribute('class', 'hex-signal');
            g.setAttribute('transform', 'translate(' + cx + ',' + cy + ')');
            g.style.pointerEvents = 'none';
            ['hex-signal-ring', 'hex-signal-ring hex-signal-ring-2'].forEach(function(cls) {
                var c = document.createElementNS(SVGNS, 'circle');
                c.setAttribute('cx', '0');
                c.setAttribute('cy', '0');
                c.setAttribute('r', String(r));
                c.setAttribute('class', cls);
                g.appendChild(c);
            });
            svg.appendChild(g);

            hook._signalTimer = setTimeout(function() {
                g.remove();
                hook._signalTimer = null;
            }, 3000);
        });
    },
    _bindClick() {
        // Remove old listener if any
        if (this._handler) {
            this.el.removeEventListener('click', this._handler);
        }
        const hook = this;
        this._handler = function(e) {
            // Walk up from clicked element to find g[data-col]
            let el = e.target;
            while (el && el !== hook.el) {
                if (el.tagName === 'g' && el.hasAttribute('data-col')) {
                    var eventName = el.hasAttribute('data-edit') ? 'set_hex' : 'hex_click';
                    hook.pushEvent(eventName, {
                        col: el.getAttribute('data-col'),
                        row: el.getAttribute('data-row')
                    });
                    return;
                }
                el = el.parentNode;
            }
        };
        this.el.addEventListener('click', this._handler);
    },
    _bindKeydown() {
        const hook = this;
        this._keyHandler = function(e) {
            if (e.key === 'Escape') {
                hook.pushEvent('close_hex_note', {});
                hook.pushEvent('close_hex_action', {});
            }
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                var form = e.target.closest && e.target.closest('form');
                if (form && hook.el.contains(form)) {
                    e.preventDefault();
                    form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
                }
            }
        };
        document.addEventListener('keydown', this._keyHandler);
    },
    _bindTimelineHover() {
        if (this._hoverCleanup) {
            this._hoverCleanup();
        }
        var cleanups = [];
        var svg = this.el.querySelector('svg');
        if (!svg) return;

        var activeGroup = null;
        var partyGroup = svg.querySelector('#party-location');

        function clearActive() {
            if (activeGroup) {
                activeGroup.classList.remove('active');
                activeGroup = null;
            }
            if (partyGroup) {
                partyGroup.style.display = '';
            }
        }

        var timeline = document.querySelector('.timeline');
        if (timeline) {
            var onMove = function(e) {
                var li = e.target.closest('[data-highlight-entry]');
                if (!li) return;
                var entryId = li.getAttribute('data-highlight-entry');
                if (activeGroup && activeGroup.getAttribute('data-entry-id') === entryId) return;
                clearActive();
                var group = svg.querySelector('[data-entry-id="' + entryId + '"]');
                if (group) {
                    group.classList.add('active');
                    activeGroup = group;
                    if (partyGroup) {
                        partyGroup.style.display = 'none';
                    }
                }
            };
            var onLeave = function() {
                clearActive();
            };

            timeline.addEventListener('mouseover', onMove);
            timeline.addEventListener('mouseleave', onLeave);
            cleanups.push(function() {
                timeline.removeEventListener('mouseover', onMove);
                timeline.removeEventListener('mouseleave', onLeave);
            });
        }

        this._hoverCleanup = function() {
            clearActive();
            cleanups.forEach(function(fn) { fn(); });
        };
    }
};

/**
 * SiteMap hook: click delegation for site map SVG elements.
 * Handles data-sm-node, data-sm-route, data-sm-entrance, data-sm-empty-node.
 */
window.Hooks.SiteMap = {
    mounted() {
        this._bindClick();
        this._bindKeydown();
    },
    updated() {
        this._bindClick();
    },
    destroyed() {
        if (this._smHandler) {
            this.el.removeEventListener('click', this._smHandler);
        }
        if (this._smKeyHandler) {
            document.removeEventListener('keydown', this._smKeyHandler);
        }
    },
    _bindClick() {
        if (this._smHandler) {
            this.el.removeEventListener('click', this._smHandler);
        }
        var hook = this;
        this._smHandler = function(e) {
            var el = e.target;
            while (el && el !== hook.el) {
                if (el.hasAttribute('data-sm-node')) {
                    hook.pushEvent('site_map_click', {
                        type: 'node',
                        id: el.getAttribute('data-sm-node')
                    });
                    return;
                }
                if (el.hasAttribute('data-sm-empty-node')) {
                    hook.pushEvent('site_map_click', {
                        type: 'empty_node',
                        id: el.getAttribute('data-sm-empty-node')
                    });
                    return;
                }
                if (el.hasAttribute('data-sm-route')) {
                    hook.pushEvent('site_map_click', {
                        type: 'route',
                        id: el.getAttribute('data-sm-route')
                    });
                    return;
                }
                if (el.hasAttribute('data-sm-entrance')) {
                    hook.pushEvent('site_map_click', {
                        type: 'entrance',
                        id: el.getAttribute('data-sm-entrance')
                    });
                    return;
                }
                el = el.parentNode;
            }
        };
        this.el.addEventListener('click', this._smHandler);
    },
    _bindKeydown() {
        var hook = this;
        this._smKeyHandler = function(e) {
            var editing = hook.el.querySelector('input:focus, textarea:focus');
            if (e.key === 'Escape') {
                if (editing) {
                    // Cancel the current field edit
                    e.preventDefault();
                    e.stopPropagation();
                    hook.pushEvent('site_map_cancel_edit', {});
                } else if (hook.el.querySelector('[data-sm-edit-mode]')) {
                    // In edit mode but not editing a field — exit edit mode
                    e.preventDefault();
                    e.stopPropagation();
                    hook.pushEvent('toggle_site_map_edit', {});
                } else {
                    // View mode — close modal
                    hook.pushEvent('close_site_map', {});
                }
                return;
            }
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && editing) {
                e.preventDefault();
                hook.pushEvent('site_map_save_edit', {});
            }
        };
        document.addEventListener('keydown', this._smKeyHandler);
    }
};
