function isLogined(fn) {
	try {
		ensureLogin(function() {
			fn();
		});
	} catch (e) {
		fn();
	}
}

var talkDomain = (function() {
	var hostname = window.location.hostname;
	if (hostname.indexOf('pre.cnsuning') > -1) {
		return 'http://talk8pre.cnsuning.com';
	} else if(hostname.indexOf('sit.cnsuning') > -1){
		return 'http://talk8sit.cnsuning.com/yunxin-web';
	} else {
		return 'http://talk8.suning.com';
	}
})();

function getWebcallParam(prdurl, pn, or, sc, prodNo) {
	var p = [];
	if (prdurl) {
		p[p.length] = ("prodUrl=" + encodeURIComponent(prdurl));
	}
	if (pn) {
		p[p.length] = ("pn=" + encodeURIComponent(pn));
	}
	if (or) {
		p[p.length] = ("r=" + encodeURIComponent(or));
	}
	if (sc) {
		p[p.length] = ("sc=" + encodeURIComponent(sc));
	}
	if (prodNo) {
		p[p.length] = ("prodNo=" + encodeURIComponent(prodNo));
	}
	p[p.length] = "url=" + encodeURIComponent(document.location.href);

	p[p.length] = "_t=" + Math.round(Math.random() * 1000000);

	return p.join("&");
}

/**
 * 打开苏宁在线客服
 * 
 * @param prdurl
 *            四级投影地址(非必须)
 * @param pn
 *            商品名称(非必须)
 * @param or
 *            订单号(非必须)
 */
function findpass(prdurl, pn, or) {
	talkpass(prdurl, pn, or);
}

/**
 * 打开苏宁在线客服的单个通道
 * 
 * @param gId
 *            通道ID
 * @param rurl
 *            客服不在线提示返回的链接地址
 * @param prdurl
 *            四级投影地址(非必须)
 * @param pn
 *            商品名称(非必须)
 * @param or
 *            订单号(非必须)
 */

function findsinglepass(gId, rurl, prdurl, pn, or) {
	var domain = talkDomain;
	var snT = sn || {};
	var channelId = gId;
	var url = domain + "/index.htm?channelId=" + channelId;
	var catalogId = snT.catalogId || '';
	var storeId = snT.storeId || '';
	if (rurl) {
		url = url + "&rurl=" + encodeURIComponent(url);
	}
	window.open(url + "&storeId=" + storeId + '&catalogId=' + catalogId + '&'
			+ getWebcallParam(prdurl, pn, or), "_blank");
}

/**
 * 打开苏宁在线客服
 * 
 * @param prdurl
 *            四级投影地址(非必须)
 * @param pn
 *            商品名称(非必须)
 * @param or
 *            订单号(非必须)
 */

function findpassNoModal(prdurl, pn, or) {
	var domain = talkDomain;
	window.open(domain + "/index.htm?" + getWebcallParam(prdurl, pn, or),
			"_blank");
}

/**
 * 四级页面打开苏宁在线客服
 * 
 * @param brandId
 *            旗舰店ID(非必须)
 * @param groupId
 *            销售类目ID
 * @param prdurl
 *            四级投影地址(非必须)
 * @param pn
 *            商品名称(非必须)
 */
function findpassBrand(brandId, groupId, prdurl, pn) {
	var domain = talkDomain;
	if (brandId) {
		window.open(domain + "/index.htm?brandId=" + brandId + "&groupId="
				+ groupId + "&" + getWebcallParam(prdurl, pn), "_blank");
	} else {
		window.open(domain + "/index.htm?groupId=" + groupId + "&"
				+ getWebcallParam(prdurl, pn), "_blank");
	}
}

/**
 * 四级页面打开供应商客服或苏宁在线客服
 * 
 * @param groupMember
 *            供应商编码(必须)
 * @param classCode
 *            商品组(必须)
 * @param brandId
 *            品牌ID(必须)
 * @param groupID
 *            销售类目ID(必须)
 * @param prdurl
 *            四级投影地址(非必须)
 * @param pn
 *            商品名称(非必须)
 */
function findpassBrand2(groupMember, classCode, brandId, groupID, prdurl, pn) {
	var snT = sn || {};
	var domain = talkDomain;
	var prodNo = snT.partNumber || '';
	var sc = snT.vendorCode || '';
	var shopCode = snT.flagshipId || '0000000000';
	var shopName = snT.flagshipName || '';
	window.open(domain + "/index.htm?groupMember=" + groupMember
			+ "&classCode=" + classCode + "&brandId=" + brandId + "&groupId="
			+ groupID + "&" + getWebcallParam(prdurl, pn, '', '', prodNo)
			+ "&sc=" + sc + "&shopCode=" + shopCode + "&rt=1", "_blank");
}

/**
 * 打开商家客服
 * 
 * @param sc
 *            商家编码(必须)
 * @param prdurl
 *            四级投影地址(非必须)
 * @param pn
 *            商品名称(非必须)
 * @param or
 *            订单号(非必须)
 */
function findpassSupplier(sc, prdurl, pn, or) {
	var domain = talkDomain;

	var snT, catalogId, storeId, prodNo;
	snT = sn || {};
	catalogId = snT.catalogId || '';
	storeId = snT.storeId || '';
	prodNo = snT.partNumber || '';
	window.open(domain + "/index.htm?catalogId=" + catalogId + '&storeId='
			+ storeId + '&' + getWebcallParam(prdurl, pn, or, sc, prodNo),
			"_blank");
}

function findpassNoModalBrand(h, f, i, j) {
	var domain = talkDomain;
	if (h != "") {
		window.open(domain + "/index.htm?brandId=" + h + "&flag=" + f
				+ "&groupId=" + i + "&url=" + encodeURIComponent(j),
				"_blank");
	} else {
		window.open(domain + "/index.htm?groupId=" + i + "&url="
				+ encodeURIComponent(j), "_blank");
	}
}

function findpassNoModalSingle() {
	var domain = talkDomain;
	window.open(domain + "/index.htm?" + getWebcallParam(), "_blank");
}

function findpassNoModal1() {
	var domain = talkDomain;
	window.open(domain + "/index.htm?" + getWebcallParam(), "_blank");
}

function findpassNoModal2() {
	var domain = talkDomain;
	window.open(domain + "/index.htm?" + getWebcallParam(), "_blank");
}

function SetCookie(f, h) {
	var snT = sn || {};
	var e = 60;
	var g = new Date;
	g.setTime(g.getTime() + e * 24 * 60 * 60 * 1000);
	document.cookie = f + "=" + escape(h) + ";domain=" + snT.cookieDomain
			+ ";expires=" + g.toGMTString();
}

function SetCookieCopy(d, c) {
	var snT = sn || {};
	document.cookie = d + "=" + escape(c) + ";path=/;domain="
			+ snT.cookieDomain;
}

function getCookie(c) {
	var d = document.cookie.match(new RegExp("(^| )" + c + "=([^;]*)(;|$)"));
	if (d != null) {
		return unescape(d[2]);
	}
	return null;
}

function delCookie() {
	var f = "tempUniqueWindow";
	var d = new Date;
	d.setTime(d.getTime() - 1);
	var e = getCookie(f);
	if (e != null) {
		document.cookie = f + "=" + e + ";expires=" + d.toGMTString();
	}
}

function CookieIsExist() {
	var b = getCookie("tempUniqueWindow");
	if (b == null) {
		SetCookieCopy("tempUniqueWindow", "openUniqueWindow");
	}
	if (b != null) {
		alert("当前聊天只支持单通道聊天");
		window.close();
		return;
	}
}

/**
 * 获得C店坐席状态
 * 
 * @param {[type]}
 *            seletor [选择器]
 * @param {[type]}
 *            sc [商家编码]
 * @param {[type]}
 *            type [类型]
 * @return {[type]} [null]
 */

function getSupplierState(seletor, sc, type) {
	var domain = talkDomain;

	var context = 'yunxin';
	var _t = new Date().getTime(), $img = $(''), type = type || 0;
	$
			.ajax({
				url : domain + '/isOnline.do',
				dataType : 'jsonp',
				data : {
					sc : sc
				},
				success : function(o) {
					if (type == 0 || type == 3) {
						if (o.channelState == 1 || o.channelState == 2) {
							$img = $('<img style="vertical-align:middle" src='
									+ domain + '/project/' + context
									+ '/images/online.gif?_t=' + _t
									+ ' alt="和我联系">');
						} else {
							$img = $('<img style="vertical-align:middle" src='
									+ domain + '/project/' + context
									+ '/images/offline.gif?_t=' + _t
									+ ' alt="和我联系">');
						}
					} else if (type == 2) {
						if (o.channelState == 1 || o.channelState == 2) {
							$img = $('<img style="vertical-align:middle" src='
									+ domain + '/project/' + context
									+ '/images/swlonline.gif?_t=' + _t
									+ ' alt="和我联系">');
						} else {
							$img = $('<img style="vertical-align:middle" src='
									+ domain + '/project/' + context
									+ '/images/swloffline.gif?_t=' + _t
									+ ' alt="和我联系">');
						}
					}
					$(seletor).html($img);
				},
				error : function() {
					if (type == 0 || type == 3) {
						$img = $('<img style="vertical-align:middle" src='
								+ domain + '/project/' + context
								+ '/images/online.gif?_t=' + _t
								+ ' alt="和我联系">');
					} else if (type == 2) {
						$img = $('<img style="vertical-align:middle" src='
								+ domain + '/project/' + context
								+ '/images/swlonline.gif?_t=' + _t
								+ ' alt="和我联系">');
					}
					$(seletor).html($img);
				}
			});
}

/**
 * [打开通道列表页,如果是vip则进入vip通道]
 * 
 * @return {[type]} [description]
 */
function talkpass(prdurl, pn, or) {
	var domain = talkDomain;
		window.open(domain + "/index.htm?" + getWebcallParam(prdurl, pn, or),
				"_blank");
}
