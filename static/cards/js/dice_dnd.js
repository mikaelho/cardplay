/**
 * Drag-and-drop assignment of situation dice.
 *
 * Mounted on a wrapper holding both the dice pool and the situation cards.
 * Dice in the pool can be dragged onto a card's die slot, dice already on a
 * card can be dragged to another card, and dragging a card's die back to the
 * pool unassigns it. The DOM move is reverted immediately -- the server
 * re-render triggered by assign_die/unassign_die is the source of truth.
 *
 * Everyone at the table shares one set of dice, so a re-render can arrive
 * mid-drag with the dragged die already taken by someone else. That drops the
 * gesture rather than acting on a die the dragger no longer sees correctly.
 */

window.Hooks = window.Hooks || {};

window.Hooks.DiceDnd = {
    mounted() {
        this._sortables = [];
        this._aborted = false;
        this._build();
    },
    beforeUpdate() {
        // Cancel before the patch lands: Sortable then puts the dragged die
        // back itself, so morphdom sees a tree it can reconcile.
        if (typeof Sortable !== 'undefined' && Sortable.active) {
            this._abort();
        }
    },
    updated() {
        this._build();
    },
    destroyed() {
        this._teardown();
    },
    _abort() {
        // Sortable has no cancel; ending the drag with the flag set makes the
        // drop handler revert the DOM and push nothing.
        this._aborted = true;
        document.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
    },
    _teardown() {
        (this._sortables || []).forEach(function (s) { s.destroy(); });
        this._sortables = [];
    },
    _build() {
        this._teardown();
        if (typeof Sortable === 'undefined') return;
        var hook = this;
        var containers = Array.prototype.slice.call(
            this.el.querySelectorAll('.dice-pool, .die-slot')
        );
        containers.forEach(function (container) {
            hook._sortables.push(new Sortable(container, {
                group: 'situation-dice',
                sort: false,
                draggable: '.die-drag',
                animation: 150,
                // Hold to drag on touch so taps still open the dropdown and
                // the page keeps scrolling normally.
                delay: 150,
                delayOnTouchOnly: true,
                touchStartThreshold: 5,
                forceFallback: true,
                fallbackTolerance: 4,
                ghostClass: 'die-drag-ghost',
                onStart: function () {
                    hook._aborted = false;
                    hook.el.classList.add('dice-dragging');
                    // Drop anything the press selected before it became a drag.
                    var sel = window.getSelection && window.getSelection();
                    if (sel && !sel.isCollapsed) sel.removeAllRanges();
                },
                onEnd: function () {
                    hook.el.classList.remove('dice-dragging');
                },
                onAdd: function (evt) {
                    hook._revert(evt);
                    if (hook._aborted) return;
                    hook._drop(evt);
                }
            }));
        });
    },
    _revert(evt) {
        evt.from.insertBefore(evt.item, evt.from.children[evt.oldIndex] || null);
    },
    _drop(evt) {
        var dieIndex = evt.item.dataset.dieIndex;
        if (dieIndex === undefined || dieIndex === '') return;
        var toCardId = evt.to.dataset.cardId;
        var fromCardId = evt.from.dataset.cardId;
        if (toCardId) {
            if (toCardId === fromCardId) return;
            this.pushEvent('assign_die', {card_id: toCardId, die_index: dieIndex});
        } else if (fromCardId) {
            this.pushEvent('unassign_die', {card_id: fromCardId, die_index: dieIndex});
        }
    }
};
