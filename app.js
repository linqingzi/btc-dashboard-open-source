/**
 * BTC Dashboard v7 — Terminal-Grade Design
 */
var syntheticDemo = false;
var uiLanguage = 'zh';
var latestPayload = null;
var loadFailure = null;
function uiText(value){return DashboardI18n.translate(value,uiLanguage)}
var staticLabels = {
  'hero-label':'综合评分','section-macro':'宏观流动性','section-etf':'ETF 资金流',
  'section-inst':'机构资金','section-sentiment':'市场情绪','section-stable':'稳定币流动性',
  'section-deriv':'衍生品指标','section-onchain':'链上数据','section-supply':'供应 & 矿工',
  'notice-link':'运行与数据说明','footer-data':'本地合成数据 · 无外部数据下载','footer-license':'MIT · 仅供开发与演示',
  'hero-title':'加载中...'
};
function setLanguage(language){
  uiLanguage=language==='en'?'en':'zh';
  document.documentElement.lang=uiLanguage==='en'?'en':'zh-CN';
  document.title=uiText('BTC Dashboard · 合成数据演示');
  Object.keys(staticLabels).forEach(function(id){var element=$(id);if(element)element.textContent=uiText(staticLabels[id])});
  ['zh','en'].forEach(function(lang){var button=$('lang-'+lang);if(button)button.setAttribute('aria-pressed',String(lang===uiLanguage))});
  if($('notice-link'))$('notice-link').setAttribute('href',uiLanguage==='en'?'README.en.md':'README.md');
  if(latestPayload)render(latestPayload);
  else if(loadFailure){txt('hero-title','数据加载失败');txt('hero-sub',loadFailure)}
}
function $(id){return document.getElementById(id)}
function txt(id,t,c){var el=$(id);if(el){el.textContent=uiText(t)||'--';if(c)el.className=c}}
function css(id,p,v){var el=$(id);if(el)el.style[p]=v}

var F={usd:function(n){if(n==null)return'--';if(Math.abs(n)>=1e12)return'$'+(n/1e12).toFixed(2)+'T';if(Math.abs(n)>=1e9)return'$'+(n/1e9).toFixed(2)+'B';return'$'+n.toLocaleString('en-US',{maximumFractionDigits:0})},pct:function(n){if(n==null)return'--';return(n>=0?'+':'')+n.toFixed(2)+'%'},num:function(n){if(n==null)return'--';return n.toLocaleString('en-US',{maximumFractionDigits:0})}}
function indicatorValue(value){if(value==null)return'—';if(typeof value==='number')return value.toLocaleString();if(typeof value==='object')return Object.keys(value).length+' 项输入';return value}

async function load(){var r=await fetch('data/latest.json');if(!r.ok)throw Error('HTTP '+r.status);var d=await r.json();if(!d.meta||d.meta.synthetic!==true)throw Error('此开源演示仅接受合成数据');return d}

// ═══ Card Builder ═══
function card(name,value,trend,bull,bear,unit,src,note){
  if(syntheticDemo)src='合成示例';
  var isBull=value!=null&&bull(value);
  var isBear=value!=null&&bear&&bear(value);
  var cls=value==null?'card miss':'card '+(isBull?'bull':isBear?'bear':'');
  
  var trendHtml='';
  if(trend!=null){
    if(trend>0.3)trendHtml='<span class=\"card-trend up\">↑ '+(trend>=0?'+':'')+trend.toFixed(1)+'%</span>';
    else if(trend<-0.3)trendHtml='<span class=\"card-trend down\">↓ '+trend.toFixed(1)+'%</span>';
  }
  
  var valHtml=value!=null?unit(value):'—';
  var noteHtml=note?note(value):'';
  
  return uiText('<div class=\"'+cls+'\">'+
    '<div class=\"card-top\"><span class=\"card-name\">'+name+'</span>'+
    (src?'<span class=\"card-src\">'+src+'</span>':'')+
    '</div>'+
    '<div class=\"card-body\"><span class=\"card-value\">'+valHtml+'</span>'+trendHtml+'</div>'+
    (noteHtml?'<div class=\"card-note\">'+noteHtml+'</div>':'')+
  '</div>');
}

function render(d){
  syntheticDemo = !!(d.meta && d.meta.synthetic);
  var p=d.price||{},m=d.market||{},mc=d.macro||{},s=d.sentiment||{},o=d.onchain||{},su=d.supply||{};
  var fng=(s.current||{}).value;
  // flat macro 数据: mc.fed_assets_trillions, mc.dxy, mc.vix, mc.yield_10y 等
  // 不再有 mc.liquidity / mc.risk / mc.treasuries / mc.inflation 嵌套层
  var liq=mc, rk=mc, tr=mc, inf=mc;

  // ── Header ──
  txt('h-price',p.usd?'$'+F.num(p.usd):'--');
  txt('h-change',F.pct(p.change_24h_pct),'header-val '+(p.change_24h_pct>=0?'up':'down'));
  txt('h-dxy',mc.dxy!=null?'DXY '+mc.dxy.toFixed(1):'--');
  txt('h-spx',rk.spx&&rk.spx.price?F.num(rk.spx.price):'--');
  txt('h-vix',rk.vix&&rk.vix.price?rk.vix.price.toFixed(1):'--');
  txt('h-fng',fng!=null?fng+(fng<=25?' 极恐':fng>=75?' 极贪':''):'--');
  txt('h-time','示例日期 '+(new Date((d.meta||{}).updated_at||Date.now())).toLocaleString(uiLanguage==='en'?'en-US':'zh-CN',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}));

  // ═══ Macro Cards ═══
  var mcCards=[];
  mcCards.push(card('Fed 总资产',liq.fed_assets_trillions,null,function(v){return v>7.5},function(v){return v<6.5},function(v){return'$'+v.toFixed(2)+'T'},'FRED',function(v){return v>7.5?'扩表 → 利好':v<6.5?'缩表中':''}));
  mcCards.push(card('M2 货币 YoY',liq.m2_yoy_pct,null,function(v){return v>5},function(v){return v<0},function(v){return(v>=0?'+':'')+v.toFixed(1)+'%'},'FRED',function(v){return v>5?'显著扩张':v<0?'收缩⚠':''}));
  mcCards.push(card('RRP 逆回购',liq.rrp_billions,null,function(v){return v<50},function(v){return v>500},function(v){return'$'+v.toFixed(0)+'B'},'FRED',function(v){return v<50?'耗尽 → 流动性释放':v>500?'吸收流动性':''}));
  mcCards.push(card('DXY 美元',mc.dxy,null,function(v){return v<98},function(v){return v>105},function(v){return v.toFixed(1)},'ICE≈',function(v){return v<98?'弱势美元':v>105?'强势美元⚠':''}));
  mcCards.push(card('实际利率 10Y',liq.real_yield_10y,null,function(v){return v<1.5},function(v){return v>3},function(v){return v.toFixed(2)+'%'},'FRED',function(v){return v<1.5?'金融条件宽松':v>3?'金融条件紧缩⚠':''}));
  mcCards.push(card('Fed 基金利率',liq.fed_funds_rate,null,function(v){return v<3.5},function(v){return v>5},function(v){return v.toFixed(2)+'%'},'FRED'));
  mcCards.push(card('CPI YoY',inf.cpi_yoy_pct,null,function(v){return v<2.5},function(v){return v>5},function(v){return v.toFixed(1)+'%'},'FRED',function(v){return v<2.5?'通胀受控':v>5?'通胀过热⚠':''}));
  mcCards.push(card('10Y 国债',tr.yield_10y,null,function(v){return v<4.5},function(v){return v>5.5},function(v){return v.toFixed(2)+'%'},'Yahoo'));
  mcCards.push(card('VIX 恐慌',rk.vix&&rk.vix.price,rk.vix&&rk.vix.change_pct,function(v){return v<18},function(v){return v>25},function(v){return v.toFixed(1)},'Yahoo',function(v){return v<18?'市场平静':v>25?'市场恐慌⚠':''}));
  mcCards.push(card('S&P 500',rk.spx&&rk.spx.price,rk.spx&&rk.spx.change_pct,function(v){return true},null,function(v){return F.num(v)},'Yahoo'));
  mcCards.push(card('铜 Dr.Copper',rk.copper&&rk.copper.price,rk.copper&&rk.copper.change_pct,function(v){return true},null,function(v){return'$'+v.toFixed(3)},'COMEX'));
  mcCards.push(card('WTI 原油',rk.oil&&rk.oil.price,rk.oil&&rk.oil.change_pct,function(v){return v<80},function(v){return v>100},function(v){return'$'+v.toFixed(2)},'NYMEX',function(v){return v<80?'低通胀压力':v>100?'高通胀':''}));

  // ── FOMC 会议卡 (升级版: 利率+会议日历+倒计时) ──
  var fomc = mc.fomc || {};
  
  // 当前 Fed Funds 利率
  if (fomc.current_rate && fomc.current_rate.effective_rate != null) {
    var rateNote = fomc.current_target_range ? '目标区间 ' + fomc.current_target_range : '';
    mcCards.push(card('Fed 基金利率', fomc.current_rate.effective_rate, null,
      function(v){return v < 3.5}, function(v){return v > 5},
      function(v){return v.toFixed(2) + '%'}, 'FRED',
      function(v){return rateNote + (v < 3.5 ? ' → 宽松' : v > 5 ? ' → 紧缩⚠' : ' → 中性')}));
  }
  
  // 下次 FOMC 会议 — 精确到年月日小时
  if (fomc.next_meeting && fomc.next_meeting.iso_date) {
    var nxt = fomc.next_meeting;
    var mtgDate = new Date(nxt.iso_date);
    var padM = (mtgDate.getMonth()+1 < 10 ? '0' : '') + (mtgDate.getMonth()+1);
    var padD = (mtgDate.getDate() < 10 ? '0' : '') + mtgDate.getDate();
    var padH = (mtgDate.getHours() < 10 ? '0' : '') + mtgDate.getHours();
    var padMin = (mtgDate.getMinutes() < 10 ? '0' : '') + mtgDate.getMinutes();
    var mtgStr = mtgDate.getFullYear() + '-' + padM + '-' + padD + ' ' + padH + ':' + padMin + ' UTC';
    var dayName = ['周日','周一','周二','周三','周四','周五','周六'][mtgDate.getDay()];
    var countdown = nxt.days_until != null ? nxt.days_until + '天后 ⏰' : '';
    mcCards.push(card('下次 FOMC', 1, null,
      function(){return false}, function(){return false},
      function(){return '📅 ' + mtgStr + ' (' + dayName + ')'}, 'Fed',
      function(){return countdown || ''}));
  }

  // 上次 FOMC 决议 — 精确到年月日小时
  if (fomc.last_decision && fomc.last_decision.iso_date) {
    var last = fomc.last_decision;
    var lastDate = new Date(last.iso_date);
    var lpadM = (lastDate.getMonth()+1 < 10 ? '0' : '') + (lastDate.getMonth()+1);
    var lpadD = (lastDate.getDate() < 10 ? '0' : '') + lastDate.getDate();
    var lpadH = (lastDate.getHours() < 10 ? '0' : '') + lastDate.getHours();
    var lpadMin = (lastDate.getMinutes() < 10 ? '0' : '') + lastDate.getMinutes();
    var lastStr = lastDate.getFullYear() + '-' + lpadM + '-' + lpadD + ' ' + lpadH + ':' + lpadMin + ' UTC';
    var agoStr = last.days_ago != null ? last.days_ago + '天前 ✅' : '';
    mcCards.push(card('上次 FOMC 决议', 1, null,
      function(){return false}, function(){return false},
      function(){return '📋 ' + lastStr}, 'Fed',
      function(){return agoStr}));
  }
  
  // FedWatch 隐含利率预测 (替代未来会议时间线)
  if (fomc.current_rate && fomc.current_rate.effective_rate != null) {
    var actualRate = fomc.current_rate.effective_rate;
    var impliedRate = mc.implied_rate;  // flat macro: implied_rate from ZQ=F
    
    if (impliedRate != null) {
      var spread = impliedRate - actualRate;
      var prediction = spread > 0.15 ? '市场定价加息' : (spread < -0.15 ? '市场定价降息' : '维持不变');
      var btcImpact = spread > 0.15 ? '利空 BTC' : (spread < -0.15 ? '利多 BTC' : '中性');
      var icon = spread > 0.15 ? '🔴' : (spread < -0.15 ? '🟢' : '🟡');
      mcCards.push(card('FedWatch 预测', 1, null,
        function(){return spread < -0.15}, function(){return spread > 0.15},
        function(){return icon + ' ' + prediction}, 'ZQ=F',
        function(){return btcImpact + ' | 实际 ' + actualRate.toFixed(2) + '% → 预期 ' + impliedRate.toFixed(2) + '%'}));
    }
  }

  $('grid-macro').innerHTML=mcCards.join('');

  // ═══ ETF Flow Cards (CoinGecko) ═══
  var etfCards=[];
  var etfData=mc.etf||{};
  var etfSymbols=[['ibit','IBIT','BlackRock'],['fbtc','FBTC','Fidelity'],['gbtc','GBTC','Grayscale'],['arkb','ARKB','ARK'],['bitb','BITB','Bitwise']];
  var totalEtfChg=0,validEtf=0;
  etfSymbols.forEach(function(s){
    var data=etfData[s[0]];
    if(data&&data.price){
      etfCards.push(card(s[1]+' '+s[2],data.price,data.change_pct,function(v){return data.change_pct>0},function(v){return data.change_pct<-1},function(v){return'$'+v.toFixed(2)},'Finnhub',function(v){return data.change_pct!=null?'24h '+(data.change_pct>=0?'+':'')+data.change_pct.toFixed(2)+'%':''}));
      if(data.change_pct!=null){totalEtfChg+=data.change_pct;validEtf++}
    }else{
      etfCards.push(card(s[1]+' '+s[2],null,null,function(){},function(){},function(v){return'—'},'ETF'));
    }
  });
  // Summary card or placeholder
  if(validEtf>0){
    var avgChg=totalEtfChg/validEtf;
    etfCards.unshift(card('ETF 综合',avgChg,null,function(v){return v>0},function(v){return v<-0.5},function(v){return(v>=0?'+':'')+v.toFixed(2)+'%'},'',function(v){return v>0.5?'资金净流入趋势':v<-0.5?'资金流出⚠':'资金平稳'}));
  } else {
    etfCards.unshift('<div class=\"card miss\"><div class=\"card-top\"><span class=\"card-name\">ETF 综合</span></div><div class=\"card-body\"><span class=\"card-value\">等待中</span></div><div class=\"card-note\">合成示例未提供此字段</div></div>');
  }
  $('grid-etf').innerHTML=uiText(etfCards.join(''));
  var inCards=[];
  inCards.push(card('24h 交易量',m.volume_24h_usd||mc.volume_24h_usd,null,function(v){return v>30e9},null,function(v){return F.usd(v)},'CoinGecko'));
  inCards.push(card('BTC 占比',m.btc_dominance_pct,null,function(v){return v>55},function(v){return v<45},function(v){return(v||0).toFixed(1)+'%'},'',function(v){return v>55?'BTC 主导':v<45?'山寨季':''}));
  inCards.push(card('链上交易额',o.bc_tx_volume_usd||o.estimated_transaction_volume_usd,null,function(v){return v>5e9},null,function(v){return F.usd(v)},'Blockchain'));
  inCards.push(card('总交易数',o.cm_tx_count||o.bc_tx_count,null,function(v){return v>500000},null,function(v){return F.num(v)},'Blockchain'));
  inCards.push(card('UTXO',o.bc_utxo_count,null,function(v){return v>100e6},null,function(v){return F.num(v)},'Blockchain'));
  inCards.push(card('交易均价',o.bc_avg_fee_usd,null,function(v){return v<5},function(v){return v>30},function(v){return'$'+(v||0).toFixed(1)},'Blockchain'));
  $('grid-inst').innerHTML=inCards.join('');

  // ═══ Stablecoin Cards (flat macro: mc.usdt_mcap, mc.usdc_mcap) ═══
  var st=mc; // flat: mc.usdt_mcap, mc.usdc_mcap, mc.stablecoin_total_mcap
  var scCards=[];
  scCards.push(card('USDT 市值',st.usdt_mcap,null,function(v){return v>100e9},null,function(v){return v!=null?'$'+(v/1e9).toFixed(1)+'B':'—'},'CoinGecko',function(v){return v>150e9?'流动性充裕':v<120e9?'收缩':''}));
  scCards.push(card('USDC 市值',st.usdc_mcap,null,function(v){return v>50e9},null,function(v){return v!=null?'$'+(v/1e9).toFixed(1)+'B':'—'},'CoinGecko'));
  scCards.push(card('稳定币总市值',st.stablecoin_total_mcap,null,function(v){return v>200e9},null,function(v){return v!=null?'$'+(v/1e9).toFixed(1)+'B':'—'},'CoinGecko',function(v){return v>250e9?'大量弹药':v<180e9?'流动性枯竭':''}));
  scCards.push(card('稳定币总交易量',st.stablecoin_total_vol,null,function(v){return v>50e9},null,function(v){return v!=null?'$'+(v/1e9).toFixed(1)+'B':'—'},'CoinGecko'));
  $('grid-stable').innerHTML=scCards.join('');

  // ═══ Sentiment Cards (sentiment.current, not sentiment.extra) ═══
  var se=s; // s.current, s.history_7d
  var sCards=[];
  // Fear & Greed
  var fngData=se.current||{};
  var fngVal=fngData.value||50;
  sCards.push(card('恐惧贪婪',fngVal,null,function(v){return v<=25},function(v){return v>=75},function(v){return v+' ('+(fngData.classification||'')+')'},'Alt.me',function(v){return v<=25?'极恐(逆向买入)':v>=75?'极贪(谨慎)':'中性'}));
    // Reddit
    var rd=se.reddit||{};
    sCards.push(card('Reddit情绪',rd.net_sentiment||0,null,function(v){return v>0},function(v){return v<0},function(v){return v>0?'+':''+v+' (净多/空)'},rd.source||'Reddit'));
    // News
    var nw=se.news||{};
    sCards.push(card('新闻情绪',nw.net_sentiment||0,null,function(v){return v>0},function(v){return v<0},function(v){return v>0?'+':''+v+' (多/空)'},nw.source||'News'));
    $('grid-sentiment').innerHTML=sCards.join('');
  var dr=mc; // flat: mc.binance_funding_rate_pct, mc.avg_funding_rate_pct 等
  var dvCards=[];
  dvCards.push(card('Binance资金费率',dr.binance_funding_rate_pct,null,function(v){return v>0},function(v){return v<-0.01},function(v){return v.toFixed(4)+'%'},'Binance'));
  dvCards.push(card('Bybit资金费率',dr.bybit_funding_rate_pct,null,function(v){return v>0},function(v){return v<-0.01},function(v){return v.toFixed(4)+'%'},'Bybit'));
  dvCards.push(card('平均资金费率',dr.avg_funding_rate_pct,null,function(v){return v>0},function(v){return v<-0.01},function(v){return v.toFixed(4)+'%'},'Combined'));
  dvCards.push(card('Basis(年化)',dr.binance_basis_pct_annual||dr.basis_pct,null,function(v){return v<5},function(v){return v>20},function(v){return (v||0).toFixed(2)+'%'},'Binance'));
  dvCards.push(card('合约OI',dr.total_oi_usd_bn,null,function(v){return v>10},null,function(v){return'$'+(v||0).toFixed(2)+'B'},'Binance+Bybit'));
  dvCards.push(card('Bybit OI',dr.bybit_oi_usd_bn,null,function(v){return v>5},null,function(v){return'$'+(v||0).toFixed(2)+'B'},'Bybit'));
  $('grid-deriv').innerHTML=dvCards.join('');

  // ═══ On-Chain Cards (Blockchain.com + CoinMetrics) ═══
  var ocCards=[];
  ocCards.push(card('活跃地址',o.cm_active_addresses||o.bc_active_addresses,null,function(v){return v>600000},null,function(v){return F.num(v)},'CoinMetrics'));
  ocCards.push(card('交易笔数',o.cm_tx_count||o.bc_tx_count,null,function(v){return v>500000},null,function(v){return F.num(v)},'Blockchain'));
  ocCards.push(card('链上交易额',o.bc_tx_volume_usd||o.estimated_transaction_volume_usd,null,function(v){return v>5e9},null,function(v){return F.usd(v)},'Blockchain'));
  ocCards.push(card('矿工收入',o.bc_miners_revenue,null,function(v){return v>20e6},null,function(v){return F.usd(v)},'Blockchain'));
  ocCards.push(card('钱包用户',o.bc_wallet_users,null,function(v){return v>80e6},null,function(v){return F.num(v)},'Blockchain'));
  ocCards.push(card('ROI 30天',o.cm_roi_30d,null,function(v){return parseFloat(v)>0},null,function(v){var n=parseFloat(v)||0;return(n>=0?'+':'')+n.toFixed(1)+'%'},'CoinMetrics'));
  ocCards.push(card('ROI 1年',o.cm_roi_1yr,null,function(v){return v>0},null,function(v){var n=parseFloat(v)||0;return(n>=0?'+':'')+n.toFixed(1)+'%'},'CoinMetrics'));
  $('grid-onchain').innerHTML=ocCards.join('');

  // ═══ Supply Cards (Blockchain.com) ═══
  var spCards=[];
  spCards.push(card('Hashrate',o.hashrate_1w_avg_eh_s,null,function(v){return v>500},null,function(v){return(v||0).toFixed(0)+' EH/s'},'Blockchain'));
  spCards.push(card('难度',o.difficulty,null,function(v){return true},null,function(v){return(v/1e12).toFixed(1)+'T'},'Blockchain'));
  spCards.push(card('区块高度',o.block_height,null,function(v){return true},null,function(v){return F.num(v)},'Blockchain'));
  spCards.push(card('日产出',su.daily_issuance_btc,null,function(v){return true},null,function(v){return(v||0).toFixed(1)+' BTC'},''));
  spCards.push(card('年通胀率',su.annual_inflation_rate_pct,null,function(v){return v<1},function(v){return v>2},function(v){return(v||0).toFixed(2)+'%'},''));
  spCards.push(card('已开采',su.percent_mined,null,function(v){return true},null,function(v){return(v||0).toFixed(1)+'%'},''));
  spCards.push(card('日均费',o.bc_avg_fee_btc,null,function(v){return v<3},null,function(v){return(v||0).toFixed(2)+' BTC'},'Blockchain'));
  $('grid-supply').innerHTML=spCards.join('');

  // ═══ Score Display (v9 连续评分系统) ═══
  var sc = d.scoring || {};
  var scoreInfo = sc.score || {};
  var bullishRatio = scoreInfo.bullish_ratio || 0;
  var weightedScore = scoreInfo.weighted_score || 0;
  var verdict = scoreInfo.verdict || '—';
  var verdictIcon = scoreInfo.verdict_icon || '⚪';
  var verdictColor = scoreInfo.verdict_color || '#666';
  var confidence = scoreInfo.confidence || 0;
  var tiers = sc.tiers || {};
  var divergenceAlerts = sc.divergence_alerts || [];
  var indicators = sc.indicators || [];

  // Hero 区域
  txt('hero-icon', verdictIcon);
  txt('hero-title', verdict);
  txt('hero-sub', 
    '看多比例 ' + bullishRatio.toFixed(1) + '% · ' +
    '加权分 ' + weightedScore.toFixed(1) + ' · ' +
    '置信度 ' + (confidence * 100).toFixed(0) + '%' +
    (divergenceAlerts.length ? ' · ⚠️ ' + divergenceAlerts.length + ' 个背离预警' : '')
  );
  txt('hero-score', bullishRatio.toFixed(1) + '%');
  
  // Hero 样式
  css('hero', 'background', verdictColor + '12');
  css('hero', 'borderColor', verdictColor + '30');
  css('hero-score', 'color', verdictColor);
  css('hero', 'borderLeft', '3px solid ' + verdictColor);

  // 分数详情面板 - 插入到 hero 下方或单独区域
  var scoreDetailHtml = '<div class="score-detail">';
  scoreDetailHtml += '<div class="score-row"><span>看多比例</span><strong>' + bullishRatio.toFixed(1) + '%</strong></div>';
  scoreDetailHtml += '<div class="score-row"><span>加权分</span><strong>' + weightedScore.toFixed(1) + ' / 100</strong></div>';
  scoreDetailHtml += '<div class="score-row"><span>置信度</span><strong>' + (confidence * 100).toFixed(0) + '%</strong></div>';
  scoreDetailHtml += '</div>';
  
  // 分层拆解
  if (tiers && Object.keys(tiers).length > 0) {
    scoreDetailHtml += '<div class="tier-breakdown">';
    ['critical', 'major', 'minor'].forEach(function(t) {
      var td = tiers[t];
      if (td && td.total > 0) {
        var label = t === 'critical' ? '🟥 Critical (核心流动性)' : 
                    t === 'major' ? '🟧 Major (货币政策/资金流)' : '🟨 Minor (风险/情绪/供应)';
        scoreDetailHtml += '<div class="tier-item">';
        scoreDetailHtml += '<div class="tier-label">' + label + '</div>';
        scoreDetailHtml += '<div class="tier-stats">';
        scoreDetailHtml += '总权重: ' + td.total + ' | ';
        scoreDetailHtml += '看多: ' + td.bullish + ' | ';
        scoreDetailHtml += '看空: ' + td.bearish + ' | ';
        scoreDetailHtml += '中性: ' + td.neutral + ' | ';
        scoreDetailHtml += '平均分: ' + td.avg_score.toFixed(3);
        scoreDetailHtml += '</div></div>';
      }
    });
    scoreDetailHtml += '</div>';
  }

  // 背离预警
  if (divergenceAlerts.length > 0) {
    scoreDetailHtml += '<div class="divergence-alerts">⚠️ 背离预警:';
    divergenceAlerts.forEach(function(a) {
      scoreDetailHtml += '<div class="alert-item">' + a + '</div>';
    });
    scoreDetailHtml += '</div>';
  }

  // 指标明细表
  if (indicators.length > 0) {
    scoreDetailHtml += '<div class="indicators-table"><table><thead><tr>';
    scoreDetailHtml += '<th>指标</th><th>数值</th><th>信号</th><th>连续分</th><th>趋势分</th><th>综合分</th><th>权重</th><th>层级</th><th>来源</th><th>解读</th>';
    scoreDetailHtml += '</tr></thead><tbody>';
    indicators.forEach(function(ind) {
      var sigClass = ind.signal === 'bullish' ? 'bull' : ind.signal === 'bearish' ? 'bear' : '';
      scoreDetailHtml += '<tr>';
      scoreDetailHtml += '<td>' + DashboardI18n.indicator(ind.name,uiLanguage) + '</td>';
      scoreDetailHtml += '<td>' + indicatorValue(ind.value) + '</td>';
      scoreDetailHtml += '<td class="' + sigClass + '">' + ({bullish:'看多',bearish:'看空',neutral:'中性'}[ind.signal] || ind.signal || '—') + '</td>';
      scoreDetailHtml += '<td>' + (ind.continuous_score != null ? ind.continuous_score.toFixed(3) : '—') + '</td>';
      scoreDetailHtml += '<td>' + (ind.trend_score != null ? ind.trend_score.toFixed(3) : '—') + '</td>';
      scoreDetailHtml += '<td>' + (ind.combined_score != null ? ind.combined_score.toFixed(3) : '—') + '</td>';
      scoreDetailHtml += '<td>' + ind.weight + '</td>';
      scoreDetailHtml += '<td>' + ({critical:'核心',major:'主要',minor:'次要'}[ind.tier] || ind.tier) + '</td>';
      scoreDetailHtml += '<td>' + (syntheticDemo ? '合成示例' : ind.source) + '</td>';
      scoreDetailHtml += '<td>' + (ind.interpretation || '') + '</td>';
      scoreDetailHtml += '</tr>';
    });
    scoreDetailHtml += '</tbody></table></div>';
  }

  scoreDetailHtml = uiText(scoreDetailHtml);

  // 插入到 hero 后面或专门区域
  var heroEl = $('hero');
  if (heroEl && heroEl.nextElementSibling && heroEl.nextElementSibling.classList.contains('score-detail')) {
    heroEl.nextElementSibling.innerHTML = scoreDetailHtml;
  } else {
    var detailDiv = document.createElement('div');
    detailDiv.className = 'score-detail';
    detailDiv.innerHTML = scoreDetailHtml;
    heroEl.parentNode.insertBefore(detailDiv, heroEl.nextSibling);
  }
}

// end of render function

async function init(){try{latestPayload=await load();render(latestPayload)}catch(e){loadFailure=e.message;txt('hero-title','数据加载失败');txt('hero-sub',loadFailure)}}
$('lang-zh').addEventListener('click',function(){setLanguage('zh')});
$('lang-en').addEventListener('click',function(){setLanguage('en')});
setLanguage('zh');
init();
