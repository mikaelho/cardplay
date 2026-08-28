/**
 * Drag-and-drop for the timeline board.
 *
 * Three independent Sortable groups, one per level, so a card can only ever be
 * dropped among peers of its own depth (this is what keeps the tree at most 3
 * levels deep — the server trusts the group boundary):
 *   - `.timeline-slot`  (group timeline-top): the horizontal row of top cards.
 *      Each slot holds at most one card; empty slots are the gaps. Occupied
 *      slots reject drops via `put`.
 *   - `.detail-zone`    (group detail-1): detail cards under a top card.
 *   - `.subdetail-zone` (group detail-2): sub-detail cards under a detail card.
 *
 * Every card carries its own detail subtree in the DOM, so moving a card moves
 * its children with it for free. The DOM move is reverted immediately: the
 * server re-render triggered by timeline_move / timeline_place is the single
 * source of truth (other players may have changed the board mid-drag).
 */

window.Hooks = window.Hooks || {};

window.Hooks.TimelineDnd = {
    mounted() {
        this._sortables = [];
        // Standard finish-editing keys for any timeline field (header + cards).
        // A field is identified by phx-blur="timeline_save"; both save by
        // blurring, which fires that event.
        //   - single-line title <input>: Enter
        //   - multiline notes <textarea>: Cmd/Ctrl+Enter (plain Enter = newline)
        this._onKeydown = function (e) {
            if (e.key !== 'Enter') return;
            var t = e.target;
            if (!t || !t.getAttribute || t.getAttribute('phx-blur') !== 'timeline_save') return;
            if (t.tagName === 'INPUT') {
                if (e.shiftKey) return;
                e.preventDefault();
                t.blur();
            } else if (t.tagName === 'TEXTAREA' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                t.blur();
            }
        };
        document.addEventListener('keydown', this._onKeydown);
        this._build();
    },
    beforeUpdate() {
        // Cancel before the patch lands so Sortable puts the dragged node back
        // and morphdom sees a tree it can reconcile.
        if (typeof Sortable !== 'undefined' && Sortable.active) {
            this._abort();
        }
    },
    updated() {
        this._build();
    },
    destroyed() {
        if (this._onKeydown) document.removeEventListener('keydown', this._onKeydown);
        this._teardown();
    },
    _abort() {
        this._aborted = true;
        document.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
    },
    _teardown() {
        (this._sortables || []).forEach(function (s) { s.destroy(); });
        this._sortables = [];
    },
    _common(extra) {
        var hook = this;
        return Object.assign({
            draggable: '.tl-card',
            animation: 150,
            delay: 150,
            delayOnTouchOnly: true,
            touchStartThreshold: 5,
            forceFallback: true,
            fallbackTolerance: 4,
            ghostClass: 'tl-ghost',
            onStart: function () {
                hook._aborted = false;
                hook.el.classList.add('dragging-tl');
                var sel = window.getSelection && window.getSelection();
                if (sel && !sel.isCollapsed) sel.removeAllRanges();
            },
            onEnd: function () {
                hook.el.classList.remove('dragging-tl');
            },
        }, extra);
    },
    _build() {
        this._teardown();
        if (typeof Sortable === 'undefined') return;
        var hook = this;

        // Top level: real slots (accept one card when empty) plus the thin
        // insert bars between them (always accept — dropping there shifts the
        // other columns right, opening a place between two cards). Both share
        // one group so a card can be dragged onto either.
        var topContainers = Array.prototype.slice.call(
            this.el.querySelectorAll('.timeline-slot, .tl-insert')
        );
        topContainers.forEach(function (container) {
            var isInsert = container.classList.contains('tl-insert');
            hook._sortables.push(new Sortable(container, hook._common({
                group: {
                    name: 'timeline-top',
                    put: isInsert
                        ? function () { return true; }
                        : function (to) { return to.el.children.length === 0; },
                },
                handle: '.tl-grip-top',
                onAdd: function (evt) {
                    var item = evt.item;
                    hook._revert(evt);
                    if (hook._aborted) return;
                    hook._dropTop(container, item);
                },
            })));
        });

        // Detail levels: ordered lists, reorder within and reparent across.
        [
            {sel: '.detail-zone', group: 'detail-1', handle: '.tl-grip-detail'},
            {sel: '.subdetail-zone', group: 'detail-2', handle: '.tl-grip-sub'},
        ].forEach(function (lvl) {
            var containers = Array.prototype.slice.call(hook.el.querySelectorAll(lvl.sel));
            containers.forEach(function (container) {
                var drop = function (evt) {
                    var item = evt.item;
                    var newIndex = evt.newIndex;
                    hook._revert(evt);
                    if (hook._aborted) return;
                    hook._dropDetail(evt.to, item, newIndex);
                };
                hook._sortables.push(new Sortable(container, hook._common({
                    group: {name: lvl.group, put: true},
                    handle: lvl.handle,
                    onAdd: drop,
                    onUpdate: drop,
                })));
            });
        });
    },
    _revert(evt) {
        evt.from.insertBefore(evt.item, evt.from.children[evt.oldIndex] || null);
    },
    _dropTop(container, item) {
        var id = item.dataset.id;
        if (!id) return;
        if (container.dataset.insert !== undefined) {
            this.pushEvent('timeline_insert_card', {id: id, at: container.dataset.insert});
        } else if (container.dataset.slot !== undefined) {
            this.pushEvent('timeline_move', {id: id, slot: container.dataset.slot});
        }
    },
    _dropDetail(toContainer, item, newIndex) {
        var id = item.dataset.id;
        if (!id) return;
        var parentId = toContainer.dataset.parent;
        if (!parentId) return;
        this.pushEvent('timeline_place', {id: id, parent_id: parentId, position: newIndex});
    },
};
