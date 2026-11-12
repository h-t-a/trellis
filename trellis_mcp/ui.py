"""Admin dashboard UI assets for the Trellis HTTP server."""

from __future__ import annotations

DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Trellis Key Dashboard</title>
<link rel="icon" href="/favicon.ico" type="image/x-icon">
<meta name="theme-color" content="#050806">
<style nonce="__NONCE__">
:root{--bg:#050806;--bg-deep:#030504;--panel:rgba(14,21,17,.82);--panel-solid:#0d1410;--line:rgba(214,244,117,.12);--line-strong:rgba(214,244,117,.24);--ink:#f4f8f2;--muted:#93a198;--muted-2:#68766d;--lime:#d6f475;--lime-strong:#e8ffa1;--mint:#7ed9a8;--sky:#5dbfff;--amber:#f4c96b;--bad:#ff8a8a;--good:#8fe6b3;--good-bg:rgba(126,217,168,.12);--warn:#f4c96b;--warn-bg:rgba(244,201,107,.12);--bad-bg:rgba(255,138,138,.12);--shadow:0 24px 70px rgba(0,0,0,.34);--radius:24px;--mono:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;--nav-h:63px;--footer-h:35px;--side-w:236px;--side-w-collapsed:88px}
:root{--logo-outline:#d6f475;--logo-primary:#d6f475;--logo-secondary:#7ed9a8;--logo-accent:#5dbfff}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;min-height:100vh;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:radial-gradient(900px 520px at 16% -10%,rgba(214,244,117,.1),transparent 60%),radial-gradient(760px 460px at 100% 0%,rgba(93,191,255,.09),transparent 55%),linear-gradient(180deg,#050806,#070b09 55%,#040605)}
body::before{content:"";position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.018) 1px,transparent 1px);background-size:64px 64px;mask-image:radial-gradient(ellipse at 50% 0%,#000 20%,transparent 78%)}
.app{display:flex;flex-direction:column;min-height:100vh;padding-bottom:var(--footer-h)}
.app::before{content:"";position:fixed;top:var(--nav-h);bottom:var(--footer-h);left:calc(max(0px,(100% - 1320px)/2) + clamp(20px,4vw,44px) + var(--side-w));width:1px;background:var(--line);pointer-events:none;z-index:1;transition:left .2s ease}
.app.auth-locked::before{display:none}
.app.sidebar-collapsed::before{left:calc(max(0px,(100% - 1320px)/2) + clamp(20px,4vw,44px) + var(--side-w-collapsed))}
.navbar{position:sticky;top:0;z-index:30;border-bottom:1px solid var(--line);background:rgba(5,8,6,.86);backdrop-filter:blur(20px)}
.navbar-inner{position:relative;display:flex;align-items:center;gap:16px;flex-wrap:wrap;width:100%;max-width:1320px;margin:0 auto;padding:10px clamp(20px,4vw,44px)}
.navbar-inner::after{content:"";position:absolute;top:0;bottom:0;left:calc(clamp(20px,4vw,44px) + var(--side-w));width:1px;background:var(--line);pointer-events:none;transition:left .2s ease}
#sidebarToggle{position:absolute;left:calc(clamp(20px,4vw,44px) + var(--side-w) - 8px);bottom:8px;z-index:2;width:34px;height:34px;border-radius:10px;transform:translateX(-100%);background:#081008;box-shadow:none;transition:left .2s ease}
body.light-mode #sidebarToggle{background:#f7fbf4;color:#36563c;border-color:rgba(54,86,60,.28)}
body.light-mode #sidebarToggle:hover{background:#eaf3e6;color:#203b27;border-color:rgba(54,86,60,.45)}
.app.sidebar-collapsed .navbar-inner::after{left:calc(clamp(20px,4vw,44px) + var(--side-w-collapsed))}
.app.sidebar-collapsed #sidebarToggle{left:calc(clamp(20px,4vw,44px) + var(--side-w-collapsed) - 8px)}
.app.sidebar-collapsed .brand{gap:0}
.app.sidebar-collapsed #sidebarToggle svg{transform:rotate(180deg)}
.icon-btn{display:grid;place-items:center;width:40px;height:40px;padding:0;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.03);color:var(--muted);cursor:pointer}
.icon-btn:hover{border-color:var(--line-strong);color:var(--ink);background:rgba(255,255,255,.06)}
.icon-btn svg{width:18px;height:18px;transition:transform .2s ease}
.shell.sidebar-collapsed .icon-btn svg{transform:rotate(180deg)}
.theme-toggle{width:auto;height:auto;padding:.4rem .7rem;border-radius:999px;font-size:.8rem;color:var(--lime);border-color:var(--line-strong);background:rgba(214,244,117,.08)}
.theme-toggle:hover{color:var(--lime-strong);border-color:var(--lime);background:rgba(214,244,117,.14)}
.theme-toggle .icon-sun{display:none}
body.light-mode .theme-toggle{color:#3f6b00;border-color:rgba(95,143,0,.35);background:rgba(95,143,0,.08)}
body.light-mode .theme-toggle:hover{color:#284700;border-color:rgba(95,143,0,.55);background:rgba(95,143,0,.14)}
body.light-mode .theme-toggle .icon-sun{display:block}
body.light-mode .theme-toggle .icon-moon{display:none}
.brand{display:flex;align-items:center;gap:12px;color:var(--ink);text-decoration:none}
.brand-mark{width:42px;height:42px;flex:0 0 auto;display:grid;place-items:center;border-radius:14px;background:linear-gradient(145deg,#162018,#0b110d);border:1px solid var(--line-strong);box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 10px 24px rgba(0,0,0,.3)}
.brand-mark svg{width:24px;height:24px;display:block}
.brand-text strong{display:block;font-size:.95rem;letter-spacing:.18em;line-height:1}
.brand-text small{display:block;margin-top:5px;font-size:.6rem;letter-spacing:.24em;color:var(--muted)}
.app.sidebar-collapsed .brand-text{display:none}
.login-brand{justify-content:center;margin:4px auto 22px;text-align:left}
.shell.auth-locked .login-brand{margin-bottom:28px}
.shell.auth-locked .login-brand .brand-mark{width:54px;height:54px;border-radius:17px}
.shell.auth-locked .login-brand .brand-text strong{font-size:1.05rem}
.shell.auth-locked #signin{display:flex;flex-direction:column;justify-content:center;position:relative;width:min(100%,calc(100vh - 110px),1000px);aspect-ratio:1/1;container-type:inline-size;margin:0 auto;padding:clamp(28px,3vw,38px) clamp(28px,3vw,38px) clamp(76px,8vw,104px);border-radius:24px}
.shell.auth-locked #signin .card-head{justify-content:center;text-align:center;margin-bottom:26px}
.shell.auth-locked #signin h2{font-size:clamp(1.5rem,2.6vw,1.85rem)}
.shell.auth-locked #signin .row{display:grid;grid-template-columns:minmax(0,1fr);gap:14px;align-items:stretch}
.shell.auth-locked #signin input{min-height:54px;font-size:1rem;border-radius:14px}
.shell.auth-locked #signin .row button{width:100%;min-height:54px;font-size:.96rem;border-radius:14px}
.shell.auth-locked #signin .row .key-visibility{width:24px;height:24px;min-height:24px;border-radius:6px;font-size:inherit}
.shell.auth-locked #signin .hint{margin-top:1rem;font-size:.84rem}
.shell.auth-locked #signin .card-head .muted{font-size:clamp(.62rem,1.35cqw,.82rem);line-height:1.5;white-space:nowrap}
.shell.auth-locked #authHint{position:absolute;left:clamp(28px,3vw,38px);right:clamp(28px,3vw,38px);bottom:clamp(28px,3vw,38px);margin:0;font-size:.82rem;white-space:nowrap;text-align:center}
.login-error{margin:12px 0 0;padding:10px 12px;border:1px solid rgba(255,138,138,.35);border-radius:12px;background:var(--bad-bg);color:var(--bad);font-size:.82rem;font-weight:650;text-align:left}
.navbar-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-left:auto}
.shell{display:grid;grid-template-columns:var(--side-w) minmax(0,1fr);gap:24px;align-items:start;width:100%;max-width:1320px;margin:0 auto;padding:0 clamp(20px,4vw,44px) 56px;transition:max-width .2s ease}
.shell.sidebar-collapsed{grid-template-columns:var(--side-w-collapsed) minmax(0,1fr)}
.req{color:var(--lime)}
.shell.auth-locked{grid-template-columns:minmax(0,1fr);align-content:center;flex:1;max-width:1100px;min-height:0;padding-top:32px;padding-bottom:32px}
.shell.auth-locked .sidebar{display:none}
.main{min-width:0;padding-top:34px}
.sidebar{position:sticky;top:var(--nav-h);display:flex;flex-direction:column;gap:20px;min-width:0;height:calc(100vh - var(--nav-h) - var(--footer-h) - 24px);overflow:hidden;padding:24px 18px 0 0}
.sidebar,.nav{scrollbar-width:none;overscroll-behavior:contain}
.sidebar-backdrop{display:none}
.nav{display:flex;flex-direction:column;gap:6px;min-height:0;overflow:visible}
.nav a{display:flex;align-items:center;gap:10px;padding:11px 12px;border:1px solid transparent;border-radius:12px;color:var(--muted);text-decoration:none;font-size:.86rem;font-weight:650;white-space:nowrap}
.nav a svg{width:18px;height:18px;flex:0 0 auto}
.nav a:hover{color:var(--ink);background:rgba(255,255,255,.03)}
.nav a.active{color:var(--lime);background:rgba(214,244,117,.07);border-color:var(--line)}
.shell.sidebar-collapsed .nav a{justify-content:center;padding:11px 0}
.shell.sidebar-collapsed .nav a span{display:none}
.shell.sidebar-collapsed .sidebar-foot{display:none}
.shell.sidebar-collapsed .sidebar{padding-right:8px}
.sidebar-foot{flex:0 0 auto;margin-top:auto;padding:16px;border:1px solid var(--line);border-radius:18px;background:rgba(255,255,255,.02)}
.side-label{display:block;margin-bottom:.55rem;font-size:.64rem;font-weight:750;letter-spacing:.14em;text-transform:uppercase;color:var(--muted-2)}
.facts-list{display:flex;flex-direction:column;gap:.45rem;margin:0;padding:0;list-style:none;font-size:.8rem;color:var(--muted)}
.facts-list li{display:flex;align-items:center;gap:8px}
.facts-list li::before{content:"";width:5px;height:5px;border-radius:50%;background:var(--lime);flex:0 0 auto}
h2{margin:0 0 .35rem;font-size:1.1rem;letter-spacing:-.02em}
p{margin:0}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:18px}
.stat{position:relative;overflow:hidden;min-height:132px;display:flex;flex-direction:column;justify-content:space-between;padding:18px;border:1px solid var(--line);border-radius:22px;background:linear-gradient(160deg,rgba(22,32,25,.86),rgba(10,16,12,.92));box-shadow:var(--shadow)}
.stat::after{content:"";position:absolute;right:-30px;top:-38px;width:116px;height:116px;border-radius:50%;background:radial-gradient(circle,rgba(214,244,117,.18),transparent 68%)}
.stat .stat-label{font-size:.68rem;font-weight:750;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.stat strong{font-size:2.05rem;font-weight:650;letter-spacing:-.04em;line-height:1}
.stat .stat-sub{font-size:.72rem;color:var(--muted)}
.stat.lime strong{color:var(--lime)}
.stat.mint strong{color:var(--mint)}
.stat.sky strong{color:var(--sky)}
.card{margin-bottom:16px;padding:22px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);box-shadow:var(--shadow);backdrop-filter:blur(18px)}
.card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;margin-bottom:18px}
.card-head .muted{max-width:44rem;line-height:1.55}
.muted{color:var(--muted)}
.small{font-size:.85rem}
.mono{font-family:var(--mono)}
.server-meta{font-size:.76rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dot{width:.7rem;height:.7rem;border-radius:50%;background:var(--muted-2);flex:0 0 auto}
.dot.good{background:var(--mint);box-shadow:0 0 0 4px rgba(126,217,168,.14),0 0 18px rgba(126,217,168,.6);animation:signal 2.2s ease-in-out infinite}
.dot.bad{background:var(--bad);box-shadow:0 0 0 4px rgba(255,138,138,.14)}
@keyframes signal{0%,100%{box-shadow:0 0 0 4px rgba(126,217,168,.14),0 0 18px rgba(126,217,168,.6)}50%{box-shadow:0 0 0 6px rgba(126,217,168,.06),0 0 26px rgba(126,217,168,.8)}}
.row{display:flex;gap:.75rem;align-items:flex-end;flex-wrap:wrap}
.field{display:flex;flex-direction:column;gap:.4rem;min-width:10rem}
.field>span{font-size:.84rem;font-weight:650;color:var(--ink)}
.field small{font-size:.76rem;color:var(--muted)}
.key-input-wrap{position:relative;display:block;width:100%;min-width:0}
.key-input-wrap input{padding-right:2.8rem}
.key-visibility{position:absolute;right:8px;top:50%;display:grid;place-items:center;width:24px;height:24px;padding:0;border:0;border-radius:6px;background:transparent;color:var(--muted);transform:translateY(-50%);pointer-events:none}
.key-visibility svg{width:15px;height:15px;pointer-events:auto}
.key-visibility .icon-eye-off{display:none}
.key-visibility.is-visible .icon-eye{display:none}
.key-visibility.is-visible .icon-eye-off{display:block}
.grow{flex:1 1 18rem}
input,select{width:100%;padding:.72rem .82rem;border:1px solid var(--line);border-radius:12px;background:#0a110d;color:var(--ink);font:inherit}
input::placeholder{color:var(--muted-2)}
input:focus,select:focus{outline:3px solid rgba(214,244,117,.16);border-color:var(--line-strong)}
button{font:inherit;font-size:.86rem;font-weight:750;padding:.7rem 1rem;border:1px solid transparent;border-radius:999px;cursor:pointer;white-space:nowrap;transition:filter .15s ease,background .15s ease,border-color .15s ease}
button:disabled{opacity:.5;cursor:not-allowed}
.primary{background:linear-gradient(135deg,var(--lime),#a8e36b);color:#081008;box-shadow:0 10px 26px rgba(168,227,107,.16)}
.primary:hover:not(:disabled){filter:brightness(1.06)}
.ghost{background:rgba(255,255,255,.03);border-color:var(--line);color:var(--ink)}
.ghost:hover:not(:disabled){border-color:var(--line-strong);background:rgba(255,255,255,.06)}
.danger{background:transparent;border-color:rgba(255,138,138,.3);color:var(--bad)}
.danger:hover:not(:disabled){background:rgba(255,138,138,.08);border-color:rgba(255,138,138,.5)}
.small.btn-compact{padding:.4rem .7rem;font-size:.8rem}
.badge{display:inline-flex;align-items:center;padding:.35rem .7rem;border:1px solid var(--line);border-radius:999px;font-size:.72rem;font-weight:750;letter-spacing:.02em;background:rgba(255,255,255,.05);color:var(--muted)}
.badge.good{background:var(--good-bg);color:var(--good);border-color:rgba(126,217,168,.24)}
.badge.warn{background:var(--warn-bg);color:var(--warn);border-color:rgba(244,201,107,.24)}
.badge.bad{background:var(--bad-bg);color:var(--bad);border-color:rgba(255,138,138,.24)}
.hint{margin-top:.8rem;font-size:.8rem;line-height:1.55;color:var(--muted)}
.hint code{padding:.1rem .32rem;border:1px solid var(--line);border-radius:6px;background:rgba(255,255,255,.04);font-family:var(--mono);font-size:.76rem}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:16px;background:rgba(0,0,0,.15)}
.head-actions{display:flex;align-items:center;gap:8px;flex-wrap:nowrap;white-space:nowrap}
.head-actions button{flex:0 0 auto;padding:.52rem .72rem;font-size:.8rem}
.table-tools{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.search-box{position:relative;flex:1 1 240px;min-width:200px}
.search-box svg{position:absolute;left:13px;top:50%;width:16px;height:16px;color:var(--muted);transform:translateY(-50%);pointer-events:none}
.search-box input{padding-left:2.4rem}
.table-tools select{width:auto;min-width:132px;flex:0 0 auto}
table{width:100%;border-collapse:collapse;min-width:700px;font-size:.9rem}
th,td{padding:.78rem .8rem;text-align:left;border-bottom:1px solid rgba(255,255,255,.06);vertical-align:middle}
th{font-size:.68rem;text-transform:uppercase;letter-spacing:.12em;color:var(--muted-2);background:rgba(255,255,255,.025)}
tr:last-child td{border-bottom:0}
tbody tr:hover{background:rgba(214,244,117,.035)}
td.actions{text-align:right;white-space:nowrap}
td.actions button+button{margin-left:6px}
th.no-col,td.no-cell{width:52px;color:var(--muted);font-variant-numeric:tabular-nums}
.pagination{display:flex;align-items:center;justify-content:flex-end;gap:10px;margin-top:12px}
.pagination button{padding:.38rem .75rem}
.page-numbers{display:flex;align-items:center;gap:4px}
.pagination .page-number{min-width:32px;padding:.38rem .5rem;border-color:transparent;background:transparent;color:var(--muted);font-variant-numeric:tabular-nums}
.pagination .page-number:hover:not(:disabled){border-color:var(--line-strong);background:rgba(255,255,255,.06);color:var(--ink)}
.pagination .page-number[aria-current="page"]{border-color:var(--lime);background:var(--lime);color:#081008}
.page-ellipsis{min-width:20px;text-align:center;color:var(--muted-2)}
.role-pill{display:inline-flex;align-items:center;padding:.24rem .58rem;border:1px solid var(--line);border-radius:999px;font-size:.68rem;font-weight:750;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.role-pill.admin{color:var(--lime);border-color:rgba(214,244,117,.24);background:rgba(214,244,117,.07)}
.role-pill.member{color:var(--sky);border-color:rgba(93,191,255,.22);background:rgba(93,191,255,.06)}
.empty{padding:2.4rem 1rem;text-align:center;color:var(--muted)}
.new-key{display:flex;flex-direction:column;gap:.8rem;margin-top:1rem;padding:1rem;border:1px solid rgba(244,201,107,.26);border-radius:16px;background:rgba(244,201,107,.06)}
.new-key strong{display:block;margin-bottom:.15rem;color:var(--amber)}
.key-line{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}
.key-line code{flex:1 1 20rem;padding:.8rem .9rem;border:1px solid var(--line);border-radius:12px;background:#050806;color:var(--lime);font-family:var(--mono);font-size:.84rem;word-break:break-all}
.modal{position:fixed;inset:0;z-index:70;display:grid;place-items:center;padding:20px}
.modal-backdrop{position:absolute;inset:0;background:rgba(2,5,3,.74);backdrop-filter:blur(8px)}
.modal-panel{position:relative;width:min(100%,560px);max-height:calc(100vh - 40px);overflow-y:auto;padding:24px;border:1px solid var(--line-strong);border-radius:24px;background:linear-gradient(165deg,#101a13,#080d0a);box-shadow:0 30px 90px rgba(0,0,0,.6)}
.confirm-panel{width:min(100%,420px)}
.modal-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:20px}
.modal-head h2{font-size:1.35rem}
.modal-close{width:36px;height:36px;border-radius:50%}
.modal-form{display:flex;flex-direction:column;gap:14px}
.modal-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:4px}
.modal .new-key{margin-top:18px}
.notice{position:fixed;right:20px;top:16px;z-index:50;max-width:min(92vw,44rem);padding:.85rem 1.1rem;border:1px solid var(--line-strong);border-radius:14px;background:var(--panel-solid);color:var(--ink);box-shadow:0 18px 44px rgba(0,0,0,.3);font-weight:650}
.notice.ok{border-color:rgba(126,217,168,.35);color:var(--good)}
.notice.warn{border-color:rgba(244,201,107,.35);color:var(--warn)}
.notice.error{border-color:rgba(255,138,138,.35);color:var(--bad)}
.site-footer{position:fixed;left:0;right:0;bottom:0;z-index:28;height:var(--footer-h);border-top:1px solid var(--line);background:rgba(5,8,6,.92);backdrop-filter:blur(16px)}
.footer-inner{display:flex;align-items:center;justify-content:space-between;gap:14px;max-width:1320px;margin:0 auto;padding:9px clamp(20px,4vw,44px);font-size:clamp(.6rem,.72vw,.7rem);color:var(--muted-2);line-height:1.45}
.footer-inner p{margin:0;white-space:nowrap;min-width:0}
.footer-note{overflow:hidden;text-overflow:ellipsis}
.footer-inner .copyright{flex:0 0 auto;color:var(--muted);letter-spacing:.04em}
.hidden{display:none!important}
.app.auth-locked .site-footer{display:none}
body.is-busy{cursor:progress}
body.light-mode{--panel:rgba(255,255,255,.9);--panel-solid:#ffffff;--line:rgba(22,52,35,.14);--line-strong:rgba(22,52,35,.28);--ink:#0d1a12;--muted:#53665b;--muted-2:#7a8a80;--lime:#5f8f00;--lime-strong:#3f6b00;--mint:#187a4d;--sky:#1670b8;--amber:#9a6b00;--bad:#b42323;--good:#167a4d;--good-bg:rgba(24,122,77,.1);--warn:#9a6b00;--warn-bg:rgba(154,107,0,.1);--bad-bg:rgba(180,35,35,.09);--shadow:0 20px 55px rgba(20,50,35,.12);background:radial-gradient(900px 520px at 16% -10%,rgba(95,143,0,.09),transparent 60%),radial-gradient(760px 460px at 100% 0%,rgba(22,112,184,.07),transparent 55%),linear-gradient(180deg,#f8fbf6,#eef5ec 55%,#f5f9f2)}
body.light-mode{--logo-outline:#5f8f00;--logo-primary:#3f6b00;--logo-secondary:#187a4d;--logo-accent:#1670b8}
body.light-mode::before{background-image:linear-gradient(rgba(20,50,35,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(20,50,35,.03) 1px,transparent 1px)}
body.light-mode .navbar{background:rgba(248,251,246,.9)}
body.light-mode .brand-mark{background:linear-gradient(145deg,#ffffff,#eaf3e6);box-shadow:inset 0 1px 0 rgba(255,255,255,.8),0 10px 24px rgba(20,50,35,.1)}
body.light-mode .icon-btn,body.light-mode .ghost{background:rgba(20,50,35,.04)}
body.light-mode .icon-btn:hover,body.light-mode .ghost:hover:not(:disabled){background:rgba(20,50,35,.08)}
body.light-mode input,body.light-mode select{background:#ffffff}
body.light-mode .stat{background:linear-gradient(160deg,rgba(255,255,255,.98),rgba(240,247,238,.98))}
body.light-mode .sidebar-foot{background:rgba(255,255,255,.62)}
body.light-mode .badge{background:rgba(20,50,35,.05)}
body.light-mode .table-wrap{background:rgba(255,255,255,.55)}
body.light-mode th{background:rgba(20,50,35,.035)}
body.light-mode tbody tr:hover{background:rgba(95,143,0,.05)}
body.light-mode .key-line code{background:#f5f9f2}
body.light-mode .modal-panel{background:linear-gradient(165deg,#ffffff,#f4f8f1)}
body.light-mode .notice{background:#ffffff}
body.light-mode .pagination .page-number:hover:not(:disabled){background:rgba(20,50,35,.08)}
body.light-mode .pagination .page-number[aria-current="page"]{color:#081008}
body.light-mode .site-footer{background:rgba(248,251,246,.94)}
@media (max-width:1080px){body{--nav-h:112px}.navbar-inner{gap:12px}.navbar-inner::after{display:none}.app::before{display:none}#sidebarToggle{position:absolute;left:auto;right:clamp(20px,4vw,44px);top:10px;bottom:auto;transform:none;box-shadow:none;background:rgba(255,255,255,.03)}.app.sidebar-collapsed .brand{gap:12px}.app.sidebar-collapsed .brand-text{display:block}.navbar-actions{width:100%;margin-left:0;justify-content:space-between}.shell,.shell.sidebar-collapsed{grid-template-columns:minmax(0,1fr)}.sidebar{position:fixed;top:var(--nav-h);right:0;bottom:var(--footer-h);z-index:41;width:min(84vw,320px);height:auto;min-height:0;overflow:hidden;padding:24px 20px;border:0;border-left:1px solid var(--line-strong);border-radius:20px 0 0 20px;background:var(--panel-solid);box-shadow:-18px 0 48px rgba(0,0,0,.24);transform:translateX(105%);visibility:hidden;pointer-events:none;transition:transform .22s ease,visibility .22s ease}.shell:not(.sidebar-collapsed):not(.auth-locked) .sidebar{transform:translateX(0);visibility:visible;pointer-events:auto}.nav{overflow:hidden}.sidebar-backdrop{display:none;position:fixed;inset:var(--nav-h) 0 var(--footer-h);z-index:40;border:0;border-radius:0;background:rgba(3,8,5,.48);backdrop-filter:blur(2px)}.shell:not(.sidebar-collapsed):not(.auth-locked) .sidebar-backdrop{display:block}}
@media (max-width:1080px){.sidebar,.nav{overflow:hidden}body.light-mode #sidebarToggle{background:#f7fbf4}}
@media (max-width:1080px){.app.sidebar-collapsed #sidebarToggle{left:auto;right:clamp(20px,4vw,44px)}}
@media (max-width:900px){body{--footer-h:56px}.shell.auth-locked #authHint{white-space:normal;position:static;margin-top:1rem}.footer-inner{flex-direction:column;align-items:flex-start;gap:2px}.footer-inner p{white-space:normal}.footer-note{overflow:visible;text-overflow:clip}}
@media (max-width:720px){.navbar-inner{padding-top:10px;padding-bottom:10px}.navbar-actions{gap:8px}.shell{padding-top:24px}.stats{grid-template-columns:1fr}.card{padding:18px}.card-head{flex-direction:column;align-items:flex-start}.row{align-items:stretch}.field{width:100%}.row button{width:100%}.pagination{flex-wrap:wrap;justify-content:flex-start}.shell.auth-locked #authHint{white-space:normal;font-size:.8rem;position:static;margin-top:1rem}.shell.auth-locked #signin{width:100%;aspect-ratio:auto;min-height:0;padding-bottom:18px}.shell.auth-locked #signin .card-head .muted{white-space:normal;font-size:.78rem}}
@media (max-width:720px){.head-actions{width:100%;gap:6px}.head-actions button{min-width:0;padding:.5rem .4rem;font-size:.76rem}}
</style>
</head>
<body>
<div class="app auth-locked">
  <header class="navbar hidden" id="mainNav">
    <div class="navbar-inner">
      <a class="brand" href="/admin/dashboard" aria-label="Trellis access console home">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <rect x="2.5" y="2.5" width="19" height="19" rx="6" stroke="var(--logo-outline)" stroke-opacity=".65"/>
            <path d="M6 8.25h12" stroke="var(--logo-primary)" stroke-width="3" stroke-linecap="round"/>
            <path d="M12 8.25V18" stroke="var(--logo-secondary)" stroke-width="3" stroke-linecap="round"/>
            <circle cx="17.5" cy="15.5" r="1.6" fill="var(--logo-accent)"/>
          </svg>
        </span>
        <span class="brand-text"><strong>TRELLIS</strong><small>MCP ACCESS</small></span>
      </a>
      <button id="sidebarToggle" type="button" class="icon-btn hidden" aria-controls="sidebar" aria-expanded="true" aria-label="Toggle sidebar" title="Collapse sidebar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="3" y="4" width="18" height="16" rx="3"/>
          <path d="M9 4v16"/>
          <path d="M15 9l-3 3 3 3"/>
        </svg>
      </button>
      <div class="navbar-actions">
        <span id="serverMeta" class="muted server-meta" aria-live="polite">-</span>
        <span id="serverDot" class="dot" title="Server status"></span>
        <button id="themeToggle" type="button" class="icon-btn theme-toggle" aria-label="Switch to light mode" title="Switch to light mode">
          <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"/></svg>
          <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="M4.9 4.9l1.4 1.4"/><path d="M17.7 17.7l1.4 1.4"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="M4.9 19.1l1.4-1.4"/><path d="M17.7 6.3l1.4-1.4"/></svg>
        </button>
        <button id="forget" type="button" class="ghost small btn-compact hidden">Sign out</button>
      </div>
    </div>
  </header>

  <div class="shell auth-locked" id="shell">
    <button id="sidebarBackdrop" class="sidebar-backdrop" type="button" aria-label="Close navigation drawer" aria-hidden="true" tabindex="-1"></button>
    <aside id="sidebar" class="sidebar" aria-label="Dashboard sections">
      <nav class="nav">
        <a class="active" href="#stats" id="navOverview" title="Overview" aria-label="Overview">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <rect x="4" y="4" width="6" height="6" rx="1.5"/><rect x="14" y="4" width="6" height="6" rx="1.5"/><rect x="4" y="14" width="6" height="6" rx="1.5"/><rect x="14" y="14" width="6" height="6" rx="1.5"/>
          </svg>
          <span>Overview</span>
        </a>
        <a href="#access" id="navAccess" title="Access Keys" aria-label="Access Keys">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="9" cy="12" r="4"/><path d="M13 12h7"/><path d="M17 12v3"/>
          </svg>
          <span>Access Keys</span>
        </a>
        <a href="#access" id="navGenerate" title="Generate Key" aria-label="Generate Key">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 5v14"/><path d="M5 12h14"/>
          </svg>
          <span>Generate Key</span>
        </a>
      </nav>
      <div class="sidebar-foot">
        <span class="side-label">Session security</span>
        <ul class="facts-list">
          <li>HttpOnly sessions</li>
          <li>15-minute TTL</li>
          <li>CSRF protected</li>
        </ul>
      </div>
    </aside>

    <main class="main">
    <section id="stats" class="stats hidden" aria-label="Key health summary">
      <article class="stat lime">
        <span class="stat-label">Active Keys</span>
        <strong id="statActive">—</strong>
        <span class="stat-sub">Ready to use</span>
      </article>
      <article class="stat sky">
        <span class="stat-label">Needs attention keys</span>
        <strong id="statAttention">—</strong>
        <span class="stat-sub">Revoked or expired</span>
      </article>
      <article class="stat mint">
        <span class="stat-label">Administrators</span>
        <strong id="statAdmins">—</strong>
        <span class="stat-sub">Can manage access</span>
      </article>
    </section>

    <section class="card" id="signin">
      <div class="brand login-brand" aria-label="Trellis MCP Access">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <rect x="2.5" y="2.5" width="19" height="19" rx="6" stroke="var(--logo-outline)" stroke-opacity=".65"/>
            <path d="M6 8.25h12" stroke="var(--logo-primary)" stroke-width="3" stroke-linecap="round"/>
            <path d="M12 8.25V18" stroke="var(--logo-secondary)" stroke-width="3" stroke-linecap="round"/>
            <circle cx="17.5" cy="15.5" r="1.6" fill="var(--logo-accent)"/>
          </svg>
        </span>
        <span class="brand-text"><strong>TRELLIS</strong><small>MCP ACCESS</small></span>
      </div>
      <div class="card-head">
        <div>
          <h2>Sign in as an Administrator</h2>
          <p class="muted">Paste an admin API key. The server exchanges it for a short-lived HttpOnly session cookie.</p>
        </div>
      </div>
      <div class="row">
        <label class="field grow" for="key">
          <span>Admin API Key <span class="req">*</span></span>
          <div class="key-input-wrap"><input id="key" type="password" autocomplete="off" spellcheck="false" placeholder="trl_admin_…" required aria-required="true"><button id="toggleKeyVisibility" type="button" class="key-visibility" aria-label="Show admin key" title="Show admin key"><svg class="icon-eye" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg><svg class="icon-eye-off" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 5.2A10.9 10.9 0 0 1 12 5c6.4 0 10 7 10 7a14 14 0 0 1-3 3.8M6.2 6.2C3.5 8 2 12 2 12s3.6 7 10 7c1.1 0 2.1-.2 3-.6"/></svg></button></div>
        </label>
        <button id="connect" type="button" class="primary">Sign in</button>
      </div>
      <p id="loginError" class="login-error hidden" role="alert"></p>
      <p id="authHint" class="hint">Tip: the server prints the first admin key once at startup. Press Enter in the field to sign in.</p>
    </section>

    <div id="workspace" class="hidden">
      <section class="card" id="access">
        <div class="card-head">
          <div>
            <h2>Active Keys</h2>
            <p class="muted">Review who can access Trellis. Edit a label or role, revoke a lost key, or generate a new one.</p>
          </div>
          <div class="head-actions">
            <button id="reload" type="button" class="ghost">Refresh</button>
            <button id="resetFilters" type="button" class="ghost">Reset</button>
            <button id="openGenerate" type="button" class="primary">Generate Key</button>
          </div>
        </div>
        <div class="table-tools">
          <label class="search-box" for="keySearch">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>
            </svg>
            <input id="keySearch" type="search" autocomplete="off" placeholder="Search label, key ID, or prefix">
          </label>
          <select id="roleFilter" aria-label="Filter by role">
            <option value="">All roles</option>
            <option value="member">Member</option>
            <option value="admin">Admin</option>
          </select>
          <select id="statusFilter" aria-label="Filter by status">
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="expired">Expired</option>
            <option value="revoked">Revoked</option>
          </select>
        </div>
        <div id="tableWrap" class="table-wrap hidden">
          <table>
            <thead>
              <tr><th class="no-col">No.</th><th>Label</th><th>Role</th><th>Prefix</th><th>Status</th><th>Created</th><th>Last used</th><th></th></tr>
            </thead>
            <tbody id="keysBody"></tbody>
          </table>
        </div>
        <div id="emptyState" class="empty hidden">No keys yet. Generate the first key.</div>
<div id="pagination" class="pagination hidden" aria-label="Key list pagination">
<button id="prevPage" type="button" class="ghost">Previous</button>
<div id="pageNumbers" class="page-numbers" aria-label="Page numbers"></div>
<button id="nextPage" type="button" class="ghost">Next</button>
</div>
      </section>
    </div>
    </main>
  </div>

  <footer class="site-footer" id="siteFooter">
    <div class="footer-inner">
      <p class="footer-note">Trellis MCP access console · Keys are stored on the server. Your admin key is exchanged for a short-lived HttpOnly session cookie. Anyone with a valid key can use its assigned role until it is revoked.</p>
      <p class="copyright">© 2026 HTA. All rights reserved.</p>
    </div>
  </footer>
</div>

<div id="generateModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="generateTitle">
  <div class="modal-backdrop" data-close-modal="generate"></div>
  <div class="modal-panel">
    <div class="modal-head">
      <div>
        <h2 id="generateTitle">Generate a key</h2>
        <p class="muted">Use <strong>Member</strong> for normal tool access. Use <strong>Admin</strong> only for people who manage keys.</p>
      </div>
      <button id="closeGenerate" type="button" class="icon-btn modal-close" aria-label="Close Generate Key dialog">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12"/><path d="M18 6L6 18"/></svg>
      </button>
    </div>
    <form id="generateForm" class="modal-form">
      <label class="field" for="label">
        <span>Label <span class="req">*</span></span>
        <input id="label" required maxlength="64" autocomplete="off" placeholder="e.g. team-ibanking">
        <small>Who or what will use this key?</small>
      </label>
      <label class="field" for="role">
        <span>Role</span>
        <select id="role">
          <option value="member">Member — use tools</option>
          <option value="admin">Admin — manage keys</option>
        </select>
      </label>
      <div class="modal-actions">
        <button id="cancelGenerate" type="button" class="ghost">Cancel</button>
        <button type="submit" class="primary">Generate Key</button>
      </div>
    </form>
    <div id="newKey" class="new-key hidden" role="status" aria-live="polite">
      <div>
        <strong>Copy this key now.</strong>
        <p class="muted">It is shown only once and cannot be recovered. Store it in a password manager.</p>
      </div>
      <div class="key-line">
        <code id="newKeyValue"></code>
        <button id="copyKey" type="button" class="ghost">Copy key</button>
      </div>
    </div>
  </div>
</div>

<div id="editModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="editTitle">
  <div class="modal-backdrop" data-close-modal="edit"></div>
  <div class="modal-panel">
    <div class="modal-head">
      <div>
        <h2 id="editTitle">Edit key</h2>
        <p class="muted">Update the label or role for this key. The key itself does not change.</p>
      </div>
      <button id="closeEdit" type="button" class="icon-btn modal-close" aria-label="Close edit key dialog">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12"/><path d="M18 6L6 18"/></svg>
      </button>
    </div>
    <form id="editForm" class="modal-form">
      <input id="editKeyId" type="hidden">
      <label class="field" for="editLabel">
        <span>Label <span class="req">*</span></span>
        <input id="editLabel" required maxlength="64" autocomplete="off">
      </label>
      <label class="field" for="editRole">
        <span>Role</span>
        <select id="editRole">
          <option value="member">Member — use tools</option>
          <option value="admin">Admin — manage keys</option>
        </select>
      </label>
      <div class="modal-actions">
        <button id="cancelEdit" type="button" class="ghost">Cancel</button>
        <button type="submit" class="primary">Save changes</button>
      </div>
    </form>
  </div>
</div>

<div id="notice" class="notice hidden" role="alert" aria-live="assertive"></div>
<div id="confirmModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="confirmTitle" aria-describedby="confirmMessage">
  <div class="modal-backdrop" data-close-modal="confirm"></div>
  <div class="modal-panel confirm-panel">
    <div class="modal-head"><div><h2 id="confirmTitle">Confirm action</h2><p id="confirmMessage" class="muted"></p></div></div>
    <div class="modal-actions"><button id="confirmCancel" type="button" class="ghost">Cancel</button><button id="confirmAccept" type="button" class="primary">Continue</button></div>
  </div>
</div>
<script nonce="__NONCE__">
const el = (id) => document.getElementById(id);
const dom = {
  key: el("key"), toggleKeyVisibility: el("toggleKeyVisibility"), connect: el("connect"), forget: el("forget"), authHint: el("authHint"), loginError: el("loginError"),
  signin: el("signin"), workspace: el("workspace"), stats: el("stats"), reload: el("reload"),
  tableWrap: el("tableWrap"), keysBody: el("keysBody"), emptyState: el("emptyState"),
  pagination: el("pagination"), pageNumbers: el("pageNumbers"), prevPage: el("prevPage"), nextPage: el("nextPage"),
  keySearch: el("keySearch"), roleFilter: el("roleFilter"), statusFilter: el("statusFilter"), resetFilters: el("resetFilters"),
  openGenerate: el("openGenerate"), generateModal: el("generateModal"), closeGenerate: el("closeGenerate"), cancelGenerate: el("cancelGenerate"),
  editModal: el("editModal"), editForm: el("editForm"), editKeyId: el("editKeyId"), editLabel: el("editLabel"), editRole: el("editRole"),
  closeEdit: el("closeEdit"), cancelEdit: el("cancelEdit"),
  generateForm: el("generateForm"), label: el("label"), role: el("role"),
  newKey: el("newKey"), newKeyValue: el("newKeyValue"), copyKey: el("copyKey"),
  notice: el("notice"), serverMeta: el("serverMeta"),
  confirmModal: el("confirmModal"), confirmMessage: el("confirmMessage"), confirmCancel: el("confirmCancel"), confirmAccept: el("confirmAccept"),
  serverDot: el("serverDot"),
  statActive: el("statActive"), statAdmins: el("statAdmins"), statAttention: el("statAttention"),
  shell: document.querySelector(".shell"), app: document.querySelector(".app"), sidebar: el("sidebar"),
  mainNav: el("mainNav"), siteFooter: el("siteFooter"),
  sidebarToggle: el("sidebarToggle"), sidebarBackdrop: el("sidebarBackdrop"), themeToggle: el("themeToggle")
};
const state = { keys: [], expiresAt: null, sidebarOpen: !window.matchMedia("(max-width: 1080px)").matches, query: "", role: "", status: "", page: 1, pageSize: 8 };
let confirmResolver = null;
let confirmReturnFocus = null;

function setNotice(message, kind) {
  const notice = dom.notice;
  notice.textContent = message;
  notice.className = "notice " + (kind || "info");
  notice.classList.remove("hidden");
  clearTimeout(setNotice.timer);
  setNotice.timer = setTimeout(() => notice.classList.add("hidden"), 3000);
}

function askForConfirmation(message, acceptLabel) {
  dom.confirmMessage.textContent = message;
  dom.confirmAccept.textContent = acceptLabel || "Continue";
  confirmReturnFocus = document.activeElement;
  dom.confirmModal.classList.remove("hidden");
  dom.confirmCancel.focus();
  return new Promise((resolve) => { confirmResolver = resolve; });
}

function finishConfirmation(accepted) {
  dom.confirmModal.classList.add("hidden");
  const resolve = confirmResolver;
  confirmResolver = null;
  if (resolve) resolve(accepted);
  if (confirmReturnFocus && typeof confirmReturnFocus.focus === "function") confirmReturnFocus.focus();
  confirmReturnFocus = null;
}

function showLoginError(message) {
  dom.loginError.textContent = "";
  dom.loginError.classList.add("hidden");
  setNotice(message, "error");
}

function clearLoginError() {
  dom.loginError.textContent = "";
  dom.loginError.classList.add("hidden");
}

function setActiveTab(id) {
  document.querySelectorAll(".nav a").forEach((link) => {
    link.classList.toggle("active", link.id === id);
  });
}

function setConnected(connected) {
  dom.mainNav.classList.toggle("hidden", !connected);
  dom.siteFooter.classList.remove("hidden");
  dom.workspace.classList.toggle("hidden", !connected);
  dom.stats.classList.toggle("hidden", !connected);
  dom.signin.classList.toggle("hidden", connected);
  dom.forget.classList.toggle("hidden", !connected);
  dom.sidebarToggle.classList.toggle("hidden", !connected);
  dom.shell.classList.toggle("auth-locked", !connected);
  dom.app.classList.toggle("auth-locked", !connected);
  if (connected) setActiveTab("navOverview");
  if (!connected) {
    dom.newKey.classList.add("hidden");
    dom.statActive.textContent = "—";
    dom.statAdmins.textContent = "—";
    dom.statAttention.textContent = "—";
  }
}

function setSidebar(open) {
  state.sidebarOpen = open;
  dom.shell.classList.toggle("sidebar-collapsed", !open);
  dom.app.classList.toggle("sidebar-collapsed", !open);
  dom.sidebarToggle.setAttribute("aria-expanded", String(open));
  const mobile = window.matchMedia("(max-width: 1080px)").matches;
  dom.sidebarToggle.title = open ? (mobile ? "Close sidebar" : "Collapse sidebar") : (mobile ? "Open sidebar" : "Expand sidebar");
  dom.sidebarBackdrop.setAttribute("aria-hidden", String(!open));
}

function applyTheme(light) {
  document.body.classList.toggle("light-mode", light);
  const label = light ? "Switch to dark mode" : "Switch to light mode";
  dom.themeToggle.setAttribute("aria-label", label);
  dom.themeToggle.title = label;
}

function setBusy(busy) {
  document.querySelectorAll("button").forEach((button) => { button.disabled = busy; });
  document.body.classList.toggle("is-busy", busy);
}

function fmtDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function isExpired(record) {
  return Boolean(record.expires_at) && new Date(record.expires_at).getTime() <= Date.now();
}

function statusOf(record) {
  if (record.revoked) return ["Revoked", "bad"];
  if (isExpired(record)) return ["Expired", "warn"];
  return ["Active", "good"];
}

async function api(path, options) {
  const opts = options || {};
  const response = await fetch(path, {
    method: opts.method || "GET",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-Trellis-CSRF": "1"
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined
  });
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch (_) { data = { raw: text }; }
  if (!response.ok) {
    if (response.status === 401) {
      setConnected(false);
      throw new Error("Your admin session expired. Sign in again.");
    }
    if (response.status === 403) throw new Error(data.message || "You do not have permission for this action.");
    throw new Error(data.message || data.error || "Request failed (" + response.status + ").");
  }
  return data;
}

async function loadServer() {
  dom.serverMeta.textContent = "-";
  dom.serverDot.className = "dot";
  try {
    const response = await fetch("/readyz", { headers: { "Accept": "application/json" } });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    dom.serverDot.className = "dot good";
    dom.serverMeta.textContent = "v" + data.version + " · " + (data.tls ? "HTTPS" : "HTTP");
  } catch (_) {
    dom.serverDot.className = "dot bad";
    dom.serverMeta.textContent = "Start the server, then refresh.";
  }
}

function matchesFilters(record) {
  if (state.role && record.role !== state.role) return false;
  if (state.status && statusOf(record)[0].toLowerCase() !== state.status) return false;
  const term = state.query.trim().toLowerCase();
  if (!term) return true;
  return [record.label, record.key_id, record.prefix, record.role]
    .some((value) => String(value || "").toLowerCase().includes(term));
}

function paginationItems(current, total) {
  const pages = new Set([1, total, current - 1, current, current + 1]);
  const sorted = Array.from(pages).filter((page) => page >= 1 && page <= total).sort((a, b) => a - b);
  const items = [];
  let previous = 0;
  sorted.forEach((page) => {
    if (previous && page - previous > 1) items.push("…");
    items.push(page);
    previous = page;
  });
  return items;
}

function renderKeys() {
  const keys = state.keys;
  dom.keysBody.replaceChildren();
  const active = keys.filter((record) => !record.revoked && !isExpired(record));
  dom.statActive.textContent = String(active.length);
  dom.statAdmins.textContent = String(active.filter((record) => record.role === "admin").length);
  dom.statAttention.textContent = String(keys.length - active.length);
  const visible = keys.filter(matchesFilters).slice().sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  const pageCount = Math.max(1, Math.ceil(visible.length / state.pageSize));
  if (state.page > pageCount) state.page = pageCount;
  const start = (state.page - 1) * state.pageSize;
  const pageItems = visible.slice(start, start + state.pageSize);
  dom.tableWrap.classList.toggle("hidden", visible.length === 0);
  dom.emptyState.classList.toggle("hidden", visible.length !== 0);
  dom.pagination.classList.toggle("hidden", pageCount <= 1);
  dom.pageNumbers.replaceChildren();
  paginationItems(state.page, pageCount).forEach((item) => {
    if (item === "…") {
      const gap = document.createElement("span");
      gap.className = "page-ellipsis";
      gap.textContent = item;
      dom.pageNumbers.appendChild(gap);
      return;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "page-number";
    button.textContent = String(item);
    button.setAttribute("aria-label", "Page " + item);
    if (item === state.page) button.setAttribute("aria-current", "page");
    button.addEventListener("click", () => {
      state.page = item;
      renderKeys();
    });
    dom.pageNumbers.appendChild(button);
  });
  dom.prevPage.disabled = state.page <= 1;
  dom.nextPage.disabled = state.page >= pageCount;
  dom.emptyState.textContent = keys.length
    ? "No keys match your search or filters."
    : "No keys yet. Generate the first key.";
  pageItems.forEach((record, index) => {
    const row = document.createElement("tr");

    const numberCell = document.createElement("td");
    numberCell.className = "no-cell";
    numberCell.textContent = String(start + index + 1);
    row.appendChild(numberCell);

    const labelCell = document.createElement("td");
    const label = document.createElement("strong");
    label.textContent = record.label || "(no label)";
    const id = document.createElement("div");
    id.className = "muted mono small";
    id.textContent = record.key_id || "";
    labelCell.append(label, id);
    row.appendChild(labelCell);

    const role = document.createElement("td");
    const rolePill = document.createElement("span");
    rolePill.className = "role-pill " + (record.role === "admin" ? "admin" : "member");
    rolePill.textContent = record.role === "admin" ? "Admin" : "Member";
    role.appendChild(rolePill);
    row.appendChild(role);

    const prefix = document.createElement("td");
    prefix.className = "mono small";
    prefix.textContent = record.prefix || "—";
    row.appendChild(prefix);

    const statusCell = document.createElement("td");
    const status = statusOf(record);
    const badge = document.createElement("span");
    badge.className = "badge " + status[1];
    badge.textContent = status[0];
    statusCell.appendChild(badge);
    row.appendChild(statusCell);

    const created = document.createElement("td");
    created.className = "small";
    created.textContent = fmtDate(record.created_at);
    row.appendChild(created);

    const used = document.createElement("td");
    used.className = "small";
    used.textContent = fmtDate(record.last_used_at);
    row.appendChild(used);

    const actions = document.createElement("td");
    actions.className = "actions";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "ghost small btn-compact";
    edit.textContent = "Edit";
    edit.addEventListener("click", () => openEdit(record));
    actions.appendChild(edit);
    if (!record.revoked && !isExpired(record)) {
      const revoke = document.createElement("button");
      revoke.type = "button";
      revoke.className = "danger small btn-compact";
      revoke.textContent = "Revoke";
      revoke.addEventListener("click", () => revokeKey(record));
      actions.appendChild(revoke);
    }
    row.appendChild(actions);
    dom.keysBody.appendChild(row);
  });
}

function openGenerateModal() {
  dom.generateForm.reset();
  dom.role.value = "member";
  dom.newKeyValue.textContent = "";
  dom.newKey.classList.add("hidden");
  dom.generateModal.classList.remove("hidden");
  dom.label.focus();
}

function closeGenerateModal() {
  dom.generateModal.classList.add("hidden");
}

function openEdit(record) {
  dom.editKeyId.value = record.key_id || "";
  dom.editLabel.value = record.label || "";
  dom.editRole.value = record.role === "admin" ? "admin" : "member";
  dom.editModal.classList.remove("hidden");
  dom.editLabel.focus();
}

function closeEditModal() {
  dom.editModal.classList.add("hidden");
}

async function loadKeys() {
  setBusy(true);
  try {
    const data = await api("/admin/keys");
    state.keys = Array.isArray(data.keys) ? data.keys : [];
    renderKeys();
    setConnected(true);
  } catch (error) {
    if (error.message.indexOf("expired") < 0) setConnected(false);
    setNotice(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function signIn() {
  const key = dom.key.value.trim();
  if (!key) {
    showLoginError("Enter an admin key first.");
    dom.key.focus();
    return;
  }
  clearLoginError();
  setBusy(true);
  try {
    const response = await fetch("/admin/session", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) throw new Error("That admin key was rejected. Check it and try again.");
      if (response.status === 403) throw new Error("That key is valid but is not an administrator key.");
      throw new Error(data.message || data.error || "Sign-in failed (" + response.status + ").");
    }
    dom.key.value = "";
    clearLoginError();
    state.expiresAt = data.expires_at || null;
    setNotice(
      state.expiresAt
        ? "Signed in until " + fmtDate(state.expiresAt) + ". This page does not store your admin key."
        : "Signed in. This page does not store your admin key.",
      "ok"
    );
    await loadKeys();
  } catch (error) {
    setConnected(false);
    setNotice(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function checkSession() {
  try {
    const response = await fetch("/admin/session", {
      headers: { "Accept": "application/json" },
      credentials: "same-origin"
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    if (data.authenticated) {
      state.expiresAt = data.expires_at || null;
      await loadKeys();
      return;
    }
  } catch (_) { /* Fall through to the signed-out state. */ }
  renderKeys();
  setConnected(false);
}

async function signOut(requireConfirmation = true) {
  if (requireConfirmation && !await askForConfirmation("Are you sure you want to sign out?", "Sign out")) return;
  setBusy(true);
  try {
    await fetch("/admin/session", {
      method: "DELETE",
      credentials: "same-origin",
      headers: { "X-Trellis-CSRF": "1" }
    });
  } catch (_) { /* Local state is cleared even if the server is unreachable. */ }
  dom.key.value = "";
  state.keys = [];
  state.expiresAt = null;
  clearLoginError();
  renderKeys();
  setConnected(false);
  dom.authHint.textContent = "Signed out. Sign in again to manage keys.";
  setNotice("Signed out.", "ok");
  setBusy(false);
}

async function revokeKey(record) {
  const name = record.label || record.key_id;
  if (!await askForConfirmation('Revoke "' + name + '"? Anyone using this key will lose access immediately.', "Revoke key")) return;
  setBusy(true);
  try {
    await api("/admin/keys/" + encodeURIComponent(record.key_id), { method: "DELETE" });
    setNotice('Revoked "' + name + '".', "ok");
    await loadKeys();
  } catch (error) {
    setNotice(error.message, "error");
  } finally {
    setBusy(false);
  }
}

dom.connect.addEventListener("click", signIn);
dom.toggleKeyVisibility.addEventListener("click", () => {
  const reveal = dom.key.type === "password";
  dom.key.type = reveal ? "text" : "password";
  const label = reveal ? "Hide admin key" : "Show admin key";
  dom.toggleKeyVisibility.classList.toggle("is-visible", reveal);
  dom.toggleKeyVisibility.setAttribute("aria-label", label);
  dom.toggleKeyVisibility.title = label;
  dom.key.focus({ preventScroll: true });
});
dom.forget.addEventListener("click", signOut);
dom.sidebarToggle.addEventListener("click", () => setSidebar(!state.sidebarOpen));
dom.sidebarBackdrop.addEventListener("click", () => setSidebar(false));
dom.sidebar.querySelectorAll(".nav a").forEach((link) => link.addEventListener("click", () => {
  if (window.matchMedia("(max-width: 1080px)").matches) setSidebar(false);
}));
dom.themeToggle.addEventListener("click", () => applyTheme(!document.body.classList.contains("light-mode")));

dom.key.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    signIn();
  }
});
dom.key.addEventListener("input", clearLoginError);

dom.reload.addEventListener("click", loadKeys);
dom.resetFilters.addEventListener("click", async () => {
  if (!await askForConfirmation("Reset filters and sign out? This will clear your current admin session.", "Reset and sign out")) return;
  dom.keySearch.value = "";
  dom.roleFilter.value = "";
  dom.statusFilter.value = "";
  state.query = "";
  state.role = "";
  state.status = "";
  state.page = 1;
  await signOut(false);
});

dom.generateForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const label = dom.label.value.trim();
  if (!label) {
    setNotice("Give the key a label so you can identify it later.", "error");
    dom.label.focus();
    return;
  }
  setBusy(true);
  try {
    const data = await api("/admin/keys", { method: "POST", body: { label: label, role: dom.role.value } });
    dom.newKeyValue.textContent = data.api_key || "";
    dom.newKey.classList.remove("hidden");
    dom.label.value = "";
    state.page = 1;
    setNotice('Created "' + label + '". Copy the key now.', "ok");
    await loadKeys();
  } catch (error) {
    setNotice(error.message, "error");
  } finally {
    setBusy(false);
  }
});

dom.copyKey.addEventListener("click", async () => {
  const value = dom.newKeyValue.textContent;
  try {
    await navigator.clipboard.writeText(value);
    setNotice("Key copied to clipboard.", "ok");
  } catch (_) {
    const range = document.createRange();
    range.selectNodeContents(dom.newKeyValue);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    setNotice("Clipboard blocked. The key is selected — press Ctrl+C.", "warn");
  }
});

dom.openGenerate.addEventListener("click", openGenerateModal);
el("navGenerate").addEventListener("click", (event) => {
  event.preventDefault();
  openGenerateModal();
});
dom.closeGenerate.addEventListener("click", closeGenerateModal);
dom.cancelGenerate.addEventListener("click", closeGenerateModal);
dom.closeEdit.addEventListener("click", closeEditModal);
dom.cancelEdit.addEventListener("click", closeEditModal);
dom.confirmCancel.addEventListener("click", () => finishConfirmation(false));
dom.confirmAccept.addEventListener("click", () => finishConfirmation(true));

document.querySelectorAll("[data-close-modal]").forEach((backdrop) => {
  backdrop.addEventListener("click", () => {
    if (backdrop.dataset.closeModal === "generate") closeGenerateModal();
    if (backdrop.dataset.closeModal === "edit") closeEditModal();
    if (backdrop.dataset.closeModal === "confirm") finishConfirmation(false);
  });
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (window.matchMedia("(max-width: 1080px)").matches && state.sidebarOpen) setSidebar(false);
    if (!dom.confirmModal.classList.contains("hidden")) finishConfirmation(false);
    closeGenerateModal();
    closeEditModal();
  }
});

dom.keySearch.addEventListener("input", () => {
  state.query = dom.keySearch.value;
  state.page = 1;
  renderKeys();
});
dom.roleFilter.addEventListener("change", () => {
  state.role = dom.roleFilter.value;
  state.page = 1;
  renderKeys();
});
dom.statusFilter.addEventListener("change", () => {
  state.status = dom.statusFilter.value;
  state.page = 1;
  renderKeys();
});
dom.prevPage.addEventListener("click", () => {
  if (state.page <= 1) return;
  state.page -= 1;
  renderKeys();
});
dom.nextPage.addEventListener("click", () => {
  const pageCount = Math.max(1, Math.ceil(state.keys.filter(matchesFilters).length / state.pageSize));
  if (state.page >= pageCount) return;
  state.page += 1;
  renderKeys();
});

dom.editForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const label = dom.editLabel.value.trim();
  if (!label) {
    setNotice("Give the key a label so you can identify it later.", "error");
    dom.editLabel.focus();
    return;
  }
  const keyId = dom.editKeyId.value;
  setBusy(true);
  try {
    const data = await api("/admin/keys/" + encodeURIComponent(keyId), {
      method: "PATCH",
      body: { label: label, role: dom.editRole.value }
    });
    const updated = data.key;
    const index = state.keys.findIndex((record) => record.key_id === updated.key_id);
    if (index >= 0) state.keys[index] = updated;
    renderKeys();
    closeEditModal();
    setNotice('Updated "' + label + '".', "ok");
  } catch (error) {
    setNotice(error.message, "error");
  } finally {
    setBusy(false);
  }
});

loadServer();
checkSession();
setSidebar(state.sidebarOpen);

document.querySelectorAll(".nav a").forEach((link) => {
  link.addEventListener("click", () => {
    if (link.id === "navGenerate") return;
    setActiveTab(link.id);
  });
});
</script>
</body>
</html>
"""
