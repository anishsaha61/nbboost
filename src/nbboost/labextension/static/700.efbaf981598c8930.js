"use strict";(self.rspackChunknbboost=self.rspackChunknbboost||[]).push([[700],{646(o,e,t){var r=t(601),n=t.n(r),a=t(314),p=(t.n(a))()(n());p.push([o.id,`/* nbboost: insert-cell bar between notebook cells */
.jp-Notebook .jp-Cell {
  position: relative;
}

.nbb-insert {
  position: absolute;
  left: 0;
  right: 0;
  bottom: -10px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.12s ease-in-out;
  z-index: 20;
}

.nbb-insert.nbb-insert-top {
  top: -10px;
  bottom: auto;
}

/* thin line across the gap, behind the buttons */
.nbb-insert::before {
  content: '';
  position: absolute;
  left: var(--jp-cell-collapser-width, 8px);
  right: 8px;
  top: 50%;
  border-top: 1px solid var(--jp-brand-color2);
  z-index: -1;
}

.nbb-insert:hover,
.nbb-insert:focus-within {
  opacity: 1;
}

.nbb-insert button {
  font-family: var(--jp-ui-font-family);
  font-size: 11px;
  font-weight: 500;
  line-height: 18px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid var(--jp-border-color1);
  background: var(--jp-layout-color1);
  color: var(--jp-ui-font-color1);
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
}

.nbb-insert button:hover,
.nbb-insert button:focus-visible {
  border-color: var(--jp-brand-color1);
  color: var(--jp-brand-color1);
  outline: none;
}

/* not in print / non-interactive views */
@media print {
  .nbb-insert {
    display: none;
  }
}

/* ------------------------------------------------------------------ */
/* Per-cell run control: [▶][⌄] in the prompt column                    */
/* ------------------------------------------------------------------ */
.jp-Notebook .jp-Cell.nbb-menu-open {
  z-index: 40;
}

.nbb-run {
  position: absolute;
  top: 11px;
  left: calc(var(--jp-cell-collapser-width, 8px) + 6px);
  display: flex;
  align-items: center;
  height: 22px;
  border-radius: 6px;
  border: 1px solid var(--jp-border-color1);
  background: var(--jp-layout-color1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  opacity: 0;
  transition: opacity 0.12s ease-in-out;
  z-index: 15;
}

.jp-Cell:hover > .nbb-run,
.jp-Cell.jp-mod-active > .nbb-run,
.nbb-run:focus-within {
  opacity: 1;
}

/* the execution count makes room while the run control is visible */
.nbb-notebook .jp-Cell:hover .jp-InputPrompt,
.nbb-notebook .jp-Cell.jp-mod-active .jp-InputPrompt {
  opacity: 0;
}

.nbb-run button {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  border: 0;
  background: transparent;
  color: var(--jp-ui-font-color1);
  cursor: pointer;
  padding: 0 6px;
}

.nbb-run .nbb-run-play {
  color: var(--jp-brand-color1);
  border-radius: 5px 0 0 5px;
}

.nbb-run .nbb-run-more {
  border-left: 1px solid var(--jp-border-color2);
  border-radius: 0 5px 5px 0;
  padding: 0 4px;
}

.nbb-run button:hover,
.nbb-run button:focus-visible {
  background: var(--jp-layout-color2);
  outline: none;
}

.nbb-run-menu {
  position: absolute;
  top: 26px;
  left: 0;
  min-width: 190px;
  padding: 4px;
  border-radius: 8px;
  border: 1px solid var(--jp-border-color1);
  background: var(--jp-layout-color0);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.18);
  z-index: 30;
}

.nbb-run-menu button {
  display: block;
  width: 100%;
  height: auto;
  text-align: left;
  font-family: var(--jp-ui-font-family);
  font-size: var(--jp-ui-font-size1);
  color: var(--jp-ui-font-color1);
  padding: 6px 10px;
  border-radius: 5px;
}

.nbb-run-menu button:hover,
.nbb-run-menu button:focus-visible {
  background: var(--jp-layout-color2);
}

/* ------------------------------------------------------------------ */
/* Notebook toolbar                                                     */
/* ------------------------------------------------------------------ */
.nbb-notebook .jp-NotebookPanel-toolbar {
  padding: 0 10px;
  gap: 2px;
  background: var(--jp-layout-color1);
  border-bottom: 1px solid var(--jp-border-color2);
  box-shadow: none;
}

.nbb-notebook .jp-NotebookPanel-toolbar .jp-ToolbarButtonComponent {
  border-radius: 6px;
}

.nbb-notebook .jp-NotebookPanel-toolbar .jp-ToolbarButtonComponent:hover {
  background: var(--jp-layout-color2);
}

.nbb-notebook .jp-Notebook-toolbarCellType select,
.nbb-notebook .jp-Notebook-toolbarCellTypeDropdown select {
  border-radius: 6px;
  border: 1px solid var(--jp-border-color2);
  padding: 0 22px 0 8px;
  background-color: var(--jp-layout-color1);
}

.nbb-notebook .jp-ToolbarButtonComponent.nbb-tb-runall {
  margin: 0 8px;
  height: 24px;
  border-radius: 6px;
  background-color: var(--jp-brand-color1);
}

.nbb-notebook .jp-ToolbarButtonComponent.nbb-tb-runall:hover {
  background-color: var(--jp-brand-color0);
}

.nbb-notebook .jp-ToolbarButtonComponent.nbb-tb-runall .jp-ToolbarButtonComponent-label {
  color: #fff;
  font-weight: 600;
  font-size: var(--jp-ui-font-size1);
  padding: 0 4px;
}

.nbb-notebook .jp-ToolbarButtonComponent.nbb-tb-runall .jp-ToolbarButtonComponent-label::before {
  content: '▶';
  font-size: 9px;
  margin-right: 6px;
  vertical-align: 1px;
}

/* group the icon buttons: file | edit | run, then the cell type */
.nbb-notebook .jp-NotebookPanel-toolbar .jp-Toolbar-item[data-jp-item-name='save'],
.nbb-notebook .jp-NotebookPanel-toolbar .jp-Toolbar-item[data-jp-item-name='paste'] {
  margin-right: 5px;
  padding-right: 5px;
  border-right: 1px solid var(--jp-border-color2);
}

.nbb-notebook .jp-NotebookPanel-toolbar .jp-KernelName {
  border: 1px solid var(--jp-border-color2);
  border-radius: 999px;
  padding: 0 10px;
  margin-right: 4px;
}

.nbb-notebook .jp-NotebookPanel-toolbar .jp-KernelName:hover {
  background: var(--jp-layout-color2);
}

/* ------------------------------------------------------------------ */
/* Cells                                                                */
/* ------------------------------------------------------------------ */
.nbb-notebook .jp-Notebook .jp-Cell {
  padding-top: 7px;
  padding-bottom: 7px;
}

.nbb-notebook .jp-Cell .jp-InputArea-editor {
  border-radius: 8px;
  border: 1px solid var(--jp-border-color2);
  background: var(--jp-layout-color0);
  overflow: hidden;
  transition: border-color 0.12s ease-in-out, box-shadow 0.12s ease-in-out;
}

.nbb-notebook .jp-Cell.jp-mod-active .jp-InputArea-editor {
  border-color: var(--jp-border-color1);
}

.nbb-notebook .jp-Notebook.jp-mod-editMode .jp-Cell.jp-mod-active .jp-InputArea-editor {
  border-color: var(--jp-brand-color1);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--jp-brand-color1) 22%, transparent);
}

.nbb-notebook .jp-InputPrompt,
.nbb-notebook .jp-OutputPrompt {
  font-size: 11px;
  opacity: 0.55;
  transition: opacity 0.12s ease-in-out;
}

.nbb-notebook .jp-Cell .jp-Collapser-child {
  border-radius: 3px;
}

.nbb-notebook .jp-MarkdownCell .jp-RenderedMarkdown {
  padding: 2px 8px;
}

.nbb-notebook .jp-Cell .jp-OutputArea-output {
  padding-top: 4px;
}

.nbb-notebook .jp-CodeCell .cm-editor,
.nbb-notebook .jp-CodeCell .cm-gutters {
  background: transparent;
}
`,""]),t.d(e,{},{A:p})},314(o){o.exports=function(o){var e=[];return e.toString=function(){return this.map(function(e){var t="",r=void 0!==e[5];return e[4]&&(t+="@supports (".concat(e[4],") {")),e[2]&&(t+="@media ".concat(e[2]," {")),r&&(t+="@layer".concat(e[5].length>0?" ".concat(e[5]):""," {")),t+=o(e),r&&(t+="}"),e[2]&&(t+="}"),e[4]&&(t+="}"),t}).join("")},e.i=function(o,t,r,n,a){"string"==typeof o&&(o=[[null,o,void 0]]);var p={};if(r)for(var b=0;b<this.length;b++){var i=this[b][0];null!=i&&(p[i]=!0)}for(var l=0;l<o.length;l++){var c=[].concat(o[l]);r&&p[c[0]]||(void 0!==a&&(void 0===c[5]||(c[1]="@layer".concat(c[5].length>0?" ".concat(c[5]):""," {").concat(c[1],"}")),c[5]=a),t&&(c[2]&&(c[1]="@media ".concat(c[2]," {").concat(c[1],"}")),c[2]=t),n&&(c[4]?(c[1]="@supports (".concat(c[4],") {").concat(c[1],"}"),c[4]=n):c[4]="".concat(n)),e.push(c))}},e}},601(o){o.exports=function(o){return o[1]}},72(o){var e=[];function t(o){for(var t=-1,r=0;r<e.length;r++)if(e[r].identifier===o){t=r;break}return t}function r(o,r){for(var n={},a=[],p=0;p<o.length;p++){var b=o[p],i=r.base?b[0]+r.base:b[0],l=n[i]||0,c="".concat(i," ").concat(l);n[i]=l+1;var s=t(c),d={css:b[1],media:b[2],sourceMap:b[3],supports:b[4],layer:b[5]};if(-1!==s)e[s].references++,e[s].updater(d);else{var u=function(o,e){var t=e.domAPI(e);return t.update(o),function(e){e?(e.css!==o.css||e.media!==o.media||e.sourceMap!==o.sourceMap||e.supports!==o.supports||e.layer!==o.layer)&&t.update(o=e):t.remove()}}(d,r);r.byIndex=p,e.splice(p,0,{identifier:c,updater:u,references:1})}a.push(c)}return a}o.exports=function(o,n){var a=r(o=o||[],n=n||{});return function(o){o=o||[];for(var p=0;p<a.length;p++){var b=t(a[p]);e[b].references--}for(var i=r(o,n),l=0;l<a.length;l++){var c=t(a[l]);0===e[c].references&&(e[c].updater(),e.splice(c,1))}a=i}}},659(o){var e={};o.exports=function(o,t){var r=function(o){if(void 0===e[o]){var t=document.querySelector(o);if(window.HTMLIFrameElement&&t instanceof window.HTMLIFrameElement)try{t=t.contentDocument.head}catch(o){t=null}e[o]=t}return e[o]}(o);if(!r)throw Error("Couldn't find a style target. This probably means that the value for the 'insert' parameter is invalid.");r.appendChild(t)}},540(o){o.exports=function(o){var e=document.createElement("style");return o.setAttributes(e,o.attributes),o.insert(e,o.options),e}},56(o,e,t){o.exports=function(o){var e=t.nc;e&&o.setAttribute("nonce",e)}},825(o){o.exports=function(o){if("u"<typeof document)return{update:function(){},remove:function(){}};var e=o.insertStyleElement(o);return{update:function(t){var r,n,a;r="",t.supports&&(r+="@supports (".concat(t.supports,") {")),t.media&&(r+="@media ".concat(t.media," {")),(n=void 0!==t.layer)&&(r+="@layer".concat(t.layer.length>0?" ".concat(t.layer):""," {")),r+=t.css,n&&(r+="}"),t.media&&(r+="}"),t.supports&&(r+="}"),(a=t.sourceMap)&&"u">typeof btoa&&(r+="\n/*# sourceMappingURL=data:application/json;base64,".concat(btoa(unescape(encodeURIComponent(JSON.stringify(a))))," */")),o.styleTagTransform(r,e,o.options)},remove:function(){var o;null===(o=e).parentNode||o.parentNode.removeChild(o)}}}},113(o){o.exports=function(o,e){if(e.styleSheet)e.styleSheet.cssText=o;else{for(;e.firstChild;)e.removeChild(e.firstChild);e.appendChild(document.createTextNode(o))}}},959(o,e,t){var r=t(72),n=t.n(r),a=t(825),p=t.n(a),b=t(659),i=t.n(b),l=t(56),c=t.n(l),s=t(540),d=t.n(s),u=t(113),v=t.n(u),x=t(646),f={};f.styleTagTransform=v(),f.setAttributes=c(),f.insert=i().bind(null,"head"),f.domAPI=p(),f.insertStyleElement=d(),n()(x.A,f),x.A&&x.A.locals&&x.A.locals}}]);