/**
 * Permanent rank adjustment on a situation card.
 *
 * The up/down arrows are wired to the ordinary click event, which shifts a
 * card temporarily. Right-clicking one (or holding it, on touch) moves the
 * baseline the card returns to instead. Delegated from the cards container so
 * it survives re-renders without rebinding each button.
 */

window.Hooks = window.Hooks || {};

var LONG_PRESS_MS = 500;

window.Hooks.LevelAdjust = {
    mounted() {
        var hook = this;

        this._onContextMenu = function (e) {
            var btn = e.target.closest('[data-baseline-delta]');
            if (!btn || !hook.el.contains(btn)) return;
            e.preventDefault();
            hook._permanent(btn);
        };

        this._onPointerDown = function (e) {
            if (e.pointerType === 'mouse') return;  // right-click covers mouse
            var btn = e.target.closest('[data-baseline-delta]');
            if (!btn || !hook.el.contains(btn)) return;
            hook._timer = setTimeout(function () {
                hook._timer = null;
                hook._fired = true;      // swallow the click this press becomes
                hook._permanent(btn);
            }, LONG_PRESS_MS);
        };

        this._cancel = function () {
            if (hook._timer) { clearTimeout(hook._timer); hook._timer = null; }
        };

        this._onClick = function (e) {
            if (!hook._fired) return;
            hook._fired = false;
            e.preventDefault();
            e.stopPropagation();
        };

        this.el.addEventListener('contextmenu', this._onContextMenu);
        this.el.addEventListener('pointerdown', this._onPointerDown);
        this.el.addEventListener('pointerup', this._cancel);
        this.el.addEventListener('pointercancel', this._cancel);
        this.el.addEventListener('pointermove', this._cancel);
        // Capture so the swallowed click never reaches the phx-click binding.
        this.el.addEventListener('click', this._onClick, true);
    },
    destroyed() {
        this._cancel();
        this.el.removeEventListener('contextmenu', this._onContextMenu);
        this.el.removeEventListener('pointerdown', this._onPointerDown);
        this.el.removeEventListener('pointerup', this._cancel);
        this.el.removeEventListener('pointercancel', this._cancel);
        this.el.removeEventListener('pointermove', this._cancel);
        this.el.removeEventListener('click', this._onClick, true);
    },
    _permanent(btn) {
        this.pushEvent('adjust_situation_card_baseline', {
            card_id: btn.dataset.cardId,
            delta: btn.dataset.baselineDelta
        });
    }
};
