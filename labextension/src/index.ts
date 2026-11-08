/**
 * nbboost JupyterLab extension.
 *
 * - A hover bar between notebook cells (and above the first one) with "+ Code",
 *   "+ Markdown" and "+ SQL" buttons. "+ SQL" inserts a code cell starting with `%%sql`.
 * - A run button on every cell with a menu: Run cell / Run all above / Run this and all below.
 * - A labelled "Run all" button in the notebook toolbar.
 * - Styling for the toolbar and cells (style/index.css).
 */
import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { ToolbarButton } from '@jupyterlab/apputils';
import {
  INotebookTracker,
  Notebook,
  NotebookActions,
  NotebookPanel
} from '@jupyterlab/notebook';
import type { Cell } from '@jupyterlab/cells';

type Kind = 'code' | 'markdown' | 'sql';
type Where = 'above' | 'below';

const BAR = 'nbb-insert';
const TOP = 'nbb-insert-top';
const LABELS: [Kind, string, string][] = [
  ['code', '+ Code', 'Insert a code cell'],
  ['markdown', '+ Markdown', 'Insert a Markdown cell'],
  ['sql', '+ SQL', 'Insert a %%sql cell']
];

/** Insert a cell next to `index` and put the cursor in it. */
export function insertCell(nb: Notebook, index: number, where: Where, kind: Kind): void {
  if (!nb.model) {
    return;
  }
  nb.activeCellIndex = Math.max(0, Math.min(index, nb.widgets.length - 1));
  nb.deselectAll();
  if (where === 'above') {
    NotebookActions.insertAbove(nb);
  } else {
    NotebookActions.insertBelow(nb);
  }
  if (kind === 'markdown') {
    NotebookActions.changeCellType(nb, 'markdown');
  }
  const cell = nb.activeCell;
  if (!cell) {
    return;
  }
  if (kind === 'sql') {
    cell.model.sharedModel.setSource('%%sql\n');
  }
  nb.mode = 'edit';
  // JupyterLab places the cursor itself when entering edit mode, so do ours afterwards
  const place = () => {
    const editor = cell.editor;
    if (!editor || cell.isDisposed) {
      return;
    }
    editor.focus();
    if (kind === 'sql') {
      editor.setCursorPosition({ line: 1, column: 0 });
    }
  };
  void cell.ready.then(() => requestAnimationFrame(place));
}

function makeBar(onPick: (kind: Kind) => void, top: boolean): HTMLElement {
  const bar = document.createElement('div');
  bar.className = top ? `${BAR} ${TOP}` : BAR;
  bar.setAttribute('role', 'toolbar');
  bar.setAttribute('aria-label', 'Insert cell');
  for (const [kind, label, title] of LABELS) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = label;
    b.title = title;
    b.dataset.kind = kind;
    // keep the notebook from treating this as a click on the cell (select / drag)
    b.addEventListener('mousedown', e => e.stopPropagation());
    b.addEventListener('pointerdown', e => e.stopPropagation());
    b.addEventListener('click', e => {
      e.preventDefault();
      e.stopPropagation();
      onPick(kind);
    });
    bar.appendChild(b);
  }
  return bar;
}

type RunMode = 'cell' | 'above' | 'below';
const RUN = 'nbb-run';
const RUN_ITEMS: [RunMode, string][] = [
  ['cell', 'Run cell'],
  ['above', 'Run all above'],
  ['below', 'Run this and all below']
];

/** Run `cell` (or the cells above it / it and the cells below it). */
export async function runFrom(panel: NotebookPanel, cell: Cell, mode: RunMode): Promise<void> {
  const nb = panel.content;
  const index = nb.widgets.indexOf(cell);
  if (index < 0) {
    return;
  }
  nb.activeCellIndex = index;
  nb.deselectAll();
  if (mode === 'cell') {
    await NotebookActions.run(nb, panel.sessionContext);
  } else if (mode === 'above') {
    await NotebookActions.runAllAbove(nb, panel.sessionContext);
  } else {
    await NotebookActions.runAllBelow(nb, panel.sessionContext);
  }
}

let openMenu: HTMLElement | null = null;
let openCell: HTMLElement | null = null;

function closeMenu(): void {
  if (openMenu) {
    openMenu.remove();
    openMenu = null;
  }
  if (openCell) {
    openCell.classList.remove('nbb-menu-open');
    openCell = null;
  }
}

document.addEventListener('mousedown', e => {
  if (openMenu && !openMenu.contains(e.target as Node)) {
    closeMenu();
  }
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeMenu();
  }
});

function stop(el: HTMLElement): void {
  el.addEventListener('mousedown', e => e.stopPropagation());
  el.addEventListener('pointerdown', e => e.stopPropagation());
  el.addEventListener('dblclick', e => e.stopPropagation());
}

function makeRunControl(panel: NotebookPanel, cell: Cell): HTMLElement {
  const box = document.createElement('div');
  box.className = RUN;
  stop(box);

  const play = document.createElement('button');
  play.type = 'button';
  play.className = 'nbb-run-play';
  play.title = 'Run cell (Shift+Enter runs and moves on)';
  play.setAttribute('aria-label', 'Run cell');
  play.innerHTML = '<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 2.5v11l9-5.5z" fill="currentColor"/></svg>';
  play.addEventListener('click', e => {
    e.preventDefault();
    e.stopPropagation();
    closeMenu();
    void runFrom(panel, cell, 'cell');
  });

  const more = document.createElement('button');
  more.type = 'button';
  more.className = 'nbb-run-more';
  more.title = 'More run options';
  more.setAttribute('aria-label', 'More run options');
  more.setAttribute('aria-haspopup', 'menu');
  more.innerHTML = '<svg viewBox="0 0 16 16" width="10" height="10" aria-hidden="true"><path d="M3.5 6l4.5 4.5L12.5 6" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';
  more.addEventListener('click', e => {
    e.preventDefault();
    e.stopPropagation();
    const wasOpen = openMenu && openMenu.parentElement === box;
    closeMenu();
    if (wasOpen) {
      return;
    }
    const menu = document.createElement('div');
    menu.className = 'nbb-run-menu';
    menu.setAttribute('role', 'menu');
    stop(menu);
    for (const [mode, label] of RUN_ITEMS) {
      const item = document.createElement('button');
      item.type = 'button';
      item.setAttribute('role', 'menuitem');
      item.dataset.mode = mode;
      item.textContent = label;
      item.addEventListener('click', ev => {
        ev.preventDefault();
        ev.stopPropagation();
        closeMenu();
        void runFrom(panel, cell, mode);
      });
      menu.appendChild(item);
    }
    box.appendChild(menu);
    openMenu = menu;
    openCell = cell.node;
    cell.node.classList.add('nbb-menu-open'); // lift above the next cells' insert bars
  });

  box.appendChild(play);
  box.appendChild(more);
  return box;
}

/** Make sure every cell has a "below" bar and only the first cell has an "above" bar. */
function decorate(panel: NotebookPanel): void {
  const nb = panel.content;
  nb.widgets.forEach((cell, i) => {
    const node = cell.node;
    if (!node.querySelector(`:scope > .${RUN}`)) {
      node.appendChild(makeRunControl(panel, cell));
    }
    if (!node.querySelector(`:scope > .${BAR}:not(.${TOP})`)) {
      node.appendChild(
        makeBar(kind => insertCell(nb, nb.widgets.indexOf(cell), 'below', kind), false)
      );
    }
    const top = node.querySelector(`:scope > .${TOP}`);
    if (i === 0 && !top) {
      node.insertBefore(
        makeBar(kind => insertCell(nb, nb.widgets.indexOf(cell), 'above', kind), true),
        node.firstChild
      );
    } else if (i !== 0 && top) {
      top.remove();
    }
  });
}

function watch(panel: NotebookPanel): void {
  let pending = false;
  const schedule = () => {
    if (pending) {
      return;
    }
    pending = true;
    // run after the notebook has created/replaced its cell widgets
    setTimeout(() => {
      pending = false;
      if (!panel.isDisposed) {
        decorate(panel);
      }
    }, 0);
  };
  const hook = () => {
    panel.content.model?.cells.changed.connect(schedule);
    schedule();
  };
  panel.content.modelChanged.connect(hook);
  void panel.context.ready.then(hook);
  hook();
  addToolbar(panel);
}

function addToolbar(panel: NotebookPanel): void {
  const runAll = new ToolbarButton({
    className: 'nbb-tb-runall',
    label: 'Run all',
    tooltip: 'Run all cells',
    onClick: () => void NotebookActions.runAll(panel.content, panel.sessionContext)
  });
  // right after the existing run / interrupt / restart buttons when present
  const names = Array.from(panel.toolbar.names());
  const after = ['restart-and-run', 'restart', 'interrupt', 'run'].find(n => names.includes(n));
  if (after) {
    panel.toolbar.insertAfter(after, 'nbboost-run-all', runAll);
  } else {
    panel.toolbar.insertItem(0, 'nbboost-run-all', runAll);
  }
  panel.node.classList.add('nbb-notebook');
}

const plugin: JupyterFrontEndPlugin<void> = {
  id: 'nbboost:insert-cell-buttons',
  description: 'Insert Code / Markdown / SQL cells from a bar between cells.',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (app: JupyterFrontEnd, tracker: INotebookTracker) => {
    tracker.forEach(watch);
    tracker.widgetAdded.connect((_, panel) => watch(panel));

    const add = (id: string, label: string, where: Where, kind: Kind) =>
      app.commands.addCommand(id, {
        label,
        isEnabled: () => !!tracker.currentWidget,
        execute: () => {
          const panel = tracker.currentWidget;
          if (panel) {
            insertCell(panel.content, panel.content.activeCellIndex, where, kind);
          }
        }
      });
    add('nbboost:insert-sql-below', 'Insert SQL Cell Below', 'below', 'sql');
    add('nbboost:insert-sql-above', 'Insert SQL Cell Above', 'above', 'sql');
    add('nbboost:insert-markdown-below', 'Insert Markdown Cell Below', 'below', 'markdown');
  }
};

export default plugin;
