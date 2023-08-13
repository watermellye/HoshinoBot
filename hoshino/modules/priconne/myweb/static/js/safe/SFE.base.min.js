function hrefLink(a) {
	if (navigator.userAgent.indexOf("Firefox") > 0) window.location = a;
	else {
		var b = document.createElement("a");
		if (b.href = a, document.body.appendChild(b), /msie/i.test(navigator.userAgent.toLowerCase())) b.click();
		else {
			var c = document.createEvent("MouseEvent");
			c.initEvent("click", !1, !1), b.dispatchEvent(c)
		}
	}
}

function d(a) {
	var b;
	return (b = document.cookie.match(RegExp("(^| )" + a + "=([^;]*)(;|$)"))) ? decodeURIComponent(b[2].replace(/\+/g, "%20")) : null
}
var SFE = SFE || {};
SFE.base = function(a) {
	function b(a, b) {
		var c = 365,
			d = new Date;
		d.setTime(d.getTime() + 24 * c * 60 * 60 * 1e3), document.cookie = a + "=" + escape(b) + ";path=/;domain=" + sn.cookieDomain + ";expires=" + d.toGMTString()
	}

	function c(b) {
		var c = k("cityId") || "9173",
			d = a(b).attr("href"),
			e = null == d.match(/cityId=.*&/gi) ? "" : "&";
		a(b).attr("href", d.replace(/cityId=.*?&|cityId=.*$/gi, "cityId=" + c + e))
	}

	function d(b) {
		var c = k("cityId") || "9173";
		url = a(b).attr("href").replace(/{cityId}/gi, c).replace(/%7bcityId%7d/gi, c), a(b).attr("href", url)
	}

	function e(a) {
		return a = a.replace(/\-/g, "%2d"), a = a.replace(/\&/g, "%26"), a = a.replace(/\./g, "%2E"), a = a.replace(/\+/g, "%2B")
	}
	var f = "https:" == document.location.protocol ? "https" : "http",
		g = !!window.ActiveXObject,
		h = g && !window.XMLHttpRequest,
		i = function(a) {
			var b = /^(\w*)(pre)(.*)(\.cnsuning\.com)$/,
				c = /^(\w*)(sit)(.*)(\.cnsuning\.com)$/;
			return b.test(a) ? "pre" : c.test(a) ? "sit" : "prd"
		},
		j = "";
	"https" == f && (j = ' src="" ');
	var k = function(a) {
			var b;
			return (b = document.cookie.match(RegExp("(^| )" + a + "=([^;]*)(;|$)"))) ? decodeURIComponent(b[2].replace(/\+/g, "%20")) : null
		},
		l = function() {
			if (void 0 == sn.passportLogon || null == sn.passportLogon) {
				var a = /^(\w*)(pre)(\w*)(.cnsuning.com)$/,
					b = /^(\w*)(sit)(\w*)(.cnsuning.com)$/,
					c = /^(\w*)(dev)(\w*)(.cnsuning.com)$/,
					d = document.location.hostname;
				sn.passportLogon = "", a.test(d) ? sn.passportLogon = "" : b.test(d) ? sn.passportLogon = "https://passportsit.cnsuning.com/ids/login" : c.test(d) && (sn.passportLogon = "https://passportdev.cnsuning.com/ids/login")
			}
			return sn.passportLogon
		},
		m = function() {
			if (void 0 == sn.passportLogoff || null == sn.passportLogoff) {
				var a = /^(\w*)(pre)(\w*)(.cnsuning.com)$/,
					b = /^(\w*)(sit)(\w*)(.cnsuning.com)$/,
					c = /^(\w*)(dev)(\w*)(.cnsuning.com)$/,
					d = document.location.hostname;
				sn.passportLogoff = "", a.test(d) ? sn.passportLogoff = "" : b.test(d) ? sn.passportLogoff = "https://passportsit.cnsuning.com/ids/logout" : c.test(d) && (sn.passportLogoff = "https://passportdev.cnsuning.com/ids/logout")
			}
			return sn.passportLogoff
		},
		n = function() {
			var a = new Date;
			a.setTime(a.getTime() - 1e4), document.cookie = "logonStatus=a; expires=" + a.toGMTString();
			var b = l(),
				c = m(),
				d = c + "?service=" + encodeURIComponent(b + "?method=GET&loginTheme=b2c");
			window.location = d, SFE.base.miniCartNum()
		},
		o = function() {
			if (!L()) {
				var a = "",
					b = "",
					c = l();
				if (void 0 == sn.sslDomain || null == sn.sslDomain) {
					var d = /^(\w*)(pre)(\w*)(.cnsuning.com)$/,
						e = /^(\w*)(sit)(\w*)(.cnsuning.com)$/,
						f = /^(\w*)(dev)(\w*)(.cnsuning.com)$/,
						g = document.location.hostname;
					sn.sslDomain = "ssl.suning.com", d.test(g) ? sn.sslDomain = "sslpre.cnsuning.com" : e.test(g) ? sn.sslDomain = "sslsit.cnsuning.com" : f.test(g) && (sn.sslDomain = "ssldev.cnsuning.com")
				}
				if (-1 != window.location.href.indexOf("&MyURL")) {
					var h = window.location.href.substring(window.location.href.indexOf("&MyURL") + 7, window.location.href.length); - 1 != h.indexOf("LogonForm") || -1 != h.indexOf("SNUserRegister") || -1 != h.indexOf("SNUserRegisterView") || -1 != h.indexOf("ForgotPasswordView") || -1 != h.indexOf("ForgotCardPswView") || -1 != h.indexOf("MobileActCode") || -1 != h.indexOf("ResetPassword") || -1 != h.indexOf("ForgotPasswordCheckMail") || -1 != h.indexOf("ForgotPasswordSendMailView") || -1 != h.indexOf("ChangeCardPwdWithIdCard") || -1 != h.indexOf("SNUserRegisterNormalMobileCmd") || -1 != h.indexOf("SNCampusMobileRegisterCmd") || -1 != h.indexOf("SNCampusEmailRegisterCmd") || -1 != h.indexOf("MbrCardInputView") || -1 != h.indexOf("SNMbrCardMergeOptionView") || -1 != h.indexOf("SNMbrCardMergeNewAccountView") || -1 != h.indexOf("SNMbrCardMergeOtherAccountView") || -1 != h.indexOf("SNMbrCardCheckCmd") || -1 != h.indexOf("SNMbrCardVerifyMyInfoCmd") || -1 != h.indexOf("SNMbrCardMergeNewAccountCmd") || -1 != h.indexOf("SNMbrCardMergeOtherAccountCmd") || -1 != h.indexOf("SNMbrCardMergeOtherVerifyMobileCmd") || -1 != h.indexOf("SNMbrCardMergeOtherVerifyEmailCmd") || -1 != h.indexOf("SNMbrCardMergeOtherVerifyNewMobileCmd") || -1 != h.indexOf("SNMbrCardMergeCmd") || -1 != h.indexOf("SNInterconnectInputView") || -1 != h.indexOf("SNInterconnectMergeCheckCmd") || -1 != h.indexOf("SNInterconnectMergeNewAccountCmd") || -1 != h.indexOf("SNInterconnectMergeOtherAccountCmd") ? (b = encodeURIComponent("http://" + sn.domain + sn.context + "/tcd_" + sn.storeId + "_" + sn.catalogId + "_.html"), a = c + "?service=" + encodeURIComponent("https://" + sn.sslDomain + "/webapp/wcs/stores/auth?targetUrl=" + b) + "&method=GET&loginTheme=b2c") : (h = decodeURIComponent(h), b = encodeURIComponent(h), a = c + "?service=" + encodeURIComponent("https://" + sn.sslDomain + "/webapp/wcs/stores/auth?targetUrl=" + b) + "&method=GET&loginTheme=b2c")
				} else if (-1 != window.location.href.indexOf("&URL")) {
					var i = window.location.href.substring(window.location.href.indexOf("&URL") + 5, window.location.href.length); - 1 != i.indexOf("LogonForm") || -1 != i.indexOf("SNUserRegister") || -1 != i.indexOf("SNUserRegisterView") || -1 != i.indexOf("ForgotPasswordView") || -1 != i.indexOf("ForgotCardPswView") || -1 != i.indexOf("MobileActCode") || -1 != i.indexOf("ResetPassword") || -1 != i.indexOf("ForgotPasswordCheckMail") || -1 != i.indexOf("ForgotPasswordSendMailView") || -1 != i.indexOf("ChangeCardPwdWithIdCard") || -1 != i.indexOf("SNUserRegisterNormalMobileCmd") || -1 != i.indexOf("SNCampusMobileRegisterCmd") || -1 != i.indexOf("SNCampusEmailRegisterCmd") || -1 != i.indexOf("MbrCardInputView") || -1 != i.indexOf("SNMbrCardMergeOptionView") || -1 != i.indexOf("SNMbrCardMergeNewAccountView") || -1 != i.indexOf("SNMbrCardMergeOtherAccountView") || -1 != i.indexOf("SNMbrCardCheckCmd") || -1 != i.indexOf("SNMbrCardVerifyMyInfoCmd") || -1 != i.indexOf("SNMbrCardMergeNewAccountCmd") || -1 != i.indexOf("SNMbrCardMergeOtherAccountCmd") || -1 != i.indexOf("SNMbrCardMergeOtherVerifyMobileCmd") || -1 != i.indexOf("SNMbrCardMergeOtherVerifyEmailCmd") || -1 != i.indexOf("SNMbrCardMergeOtherVerifyNewMobileCmd") || -1 != i.indexOf("SNMbrCardMergeCmd") || -1 != i.indexOf("SNInterconnectInputView") || -1 != i.indexOf("SNInterconnectMergeCheckCmd") || -1 != i.indexOf("SNInterconnectMergeNewAccountCmd") || -1 != i.indexOf("SNInterconnectMergeOtherAccountCmd") ? (b = encodeURIComponent("http://" + sn.domain + sn.context + "/tcd_" + sn.storeId + "_" + sn.catalogId + "_.html"), a = c + "?service=" + encodeURIComponent("https://" + sn.sslDomain + "/webapp/wcs/stores/auth?targetUrl=" + b) + "&method=GET&loginTheme=b2c") : (i = decodeURIComponent(i), b = encodeURIComponent(i), a = c + "?service=" + encodeURIComponent("https://" + sn.sslDomain + "/webapp/wcs/stores/auth?targetUrl=" + b) + "&method=GET&loginTheme=b2c")
				} else {
					var j = window.location.href.substring(window.location.href.lastIndexOf("/") + 1, window.location.href.length); - 1 != j.indexOf("LogonForm") || -1 != j.indexOf("SNUserRegister") || -1 != j.indexOf("SNUserRegisterView") || -1 != j.indexOf("ForgotPasswordView") || -1 != j.indexOf("ForgotCardPswView") || -1 != j.indexOf("MobileActCode") || -1 != j.indexOf("ResetPassword") || -1 != j.indexOf("ForgotPasswordCheckMail") || -1 != j.indexOf("ForgotPasswordSendMailView") || -1 != j.indexOf("ChangeCardPwdWithIdCard") || -1 != j.indexOf("SNUserRegisterNormalMobileCmd") || -1 != j.indexOf("SNCampusMobileRegisterCmd") || -1 != j.indexOf("SNCampusEmailRegisterCmd") || -1 != j.indexOf("MbrCardInputView") || -1 != j.indexOf("SNMbrCardMergeOptionView") || -1 != j.indexOf("SNMbrCardMergeNewAccountView") || -1 != j.indexOf("SNMbrCardMergeOtherAccountView") || -1 != j.indexOf("SNMbrCardCheckCmd") || -1 != j.indexOf("SNMbrCardVerifyMyInfoCmd") || -1 != j.indexOf("SNMbrCardMergeNewAccountCmd") || -1 != j.indexOf("SNMbrCardMergeOtherAccountCmd") || -1 != j.indexOf("SNMbrCardMergeOtherVerifyMobileCmd") || -1 != j.indexOf("SNMbrCardMergeOtherVerifyEmailCmd") || -1 != j.indexOf("SNMbrCardMergeOtherVerifyNewMobileCmd") || -1 != j.indexOf("SNMbrCardMergeCmd") || -1 != j.indexOf("SNInterconnectInputView") || -1 != j.indexOf("SNInterconnectMergeCheckCmd") || -1 != j.indexOf("SNInterconnectMergeNewAccountCmd") || -1 != j.indexOf("SNInterconnectMergeOtherAccountCmd") ? (b = encodeURIComponent("http://" + sn.domain + sn.context + "/tcd_" + sn.storeId + "_" + sn.catalogId + "_.html"), a = c + "?service=" + encodeURIComponent("https://" + sn.sslDomain + "/webapp/wcs/stores/auth?targetUrl=" + b) + "&method=GET&loginTheme=b2c") : -1 != window.location.href.substring(window.location.href.lastIndexOf("/") + 1, window.location.href.length).indexOf("CxnyProductSearch") ? (b = encodeURIComponent(window.location.href), a = c + "?service=" + encodeURIComponent("https://" + sn.sslDomain + "/webapp/wcs/stores/auth?targetUrl=" + b) + "&method=GET&loginTheme=b2c") : "" == window.location.href.substring(window.location.href.lastIndexOf("/") + 1, window.location.href.length) && null == window.location.href.match("(.*?suning.com.*?)") ? (b = encodeURIComponent("http://" + sn.domain), a = c + "?service=" + encodeURIComponent("https://" + sn.sslDomain + "/webapp/wcs/stores/auth?targetUrl=" + b) + "&method=GET&loginTheme=b2c") : (b = encodeURIComponent(window.location.href), a = c + "?service=" + encodeURIComponent("https://" + sn.sslDomain + "/webapp/wcs/stores/auth?targetUrl=" + b) + "&method=GET&loginTheme=b2c")
				}
				hrefLink(a)
			}
		},
		p = function() {
			var a = "";
			if (void 0 == sn.sslDomain || null == sn.sslDomain) {
				var b = /^(\w*)(pre)(\w*)(.cnsuning.com)$/,
					c = /^(\w*)(sit)(\w*)(.cnsuning.com)$/,
					d = /^(\w*)(dev)(\w*)(.cnsuning.com)$/,
					e = document.location.hostname;
				sn.sslDomain = "", b.test(e) ? sn.sslDomain = "" : c.test(e) ? sn.sslDomain = "" : d.test(e) && (sn.sslDomain = "")
			}
			if (-1 != window.location.href.indexOf("&URL")) a = window.location.href.substring(window.location.href.indexOf("&URL") + 5, window.location.href.length), a = -1 != a.indexOf("LogonForm") || -1 != a.indexOf("SNUserRegisterView") || -1 != a.indexOf("ForgotPasswordView") || -1 != a.indexOf("SNUserRegisterView") || -1 != a.indexOf("ForgotPasswordCheckMail") || -1 != a.indexOf("ForgotPasswordSendMailView") || -1 != a.indexOf("ChangeCardPwdWithIdCard") ? "https://" + sn.sslDomain + sn.context + "/SNUserRegisterView?storeId=" + sn.storeId + "&catalogId=" + sn.catalogId + "&MyURL=" + encodeURIComponent("http://" + sn.domain + sn.context + "/tcd_" + sn.storeId + "_" + sn.catalogId + "_.html") : "https://" + sn.sslDomain + sn.context + "/SNUserRegisterView?storeId=" + sn.storeId + "&catalogId=" + sn.catalogId + "&MyURL=" + a;
			else if (-1 != window.location.href.indexOf("&MyURL")) {
				var f = window.location.href.substring(window.location.href.indexOf("&MyURL") + 7, window.location.href.length);
				a = -1 != f.indexOf("LogonForm") || -1 != f.indexOf("SNUserRegisterView") || -1 != f.indexOf("ForgotPasswordView") || -1 != f.indexOf("SNUserRegisterView") || -1 != f.indexOf("ForgotPasswordCheckMail") || -1 != f.indexOf("ForgotPasswordSendMailView") || -1 != f.indexOf("ChangeCardPwdWithIdCard") ? "https://" + sn.sslDomain + sn.context + "/SNUserRegisterView?storeId=" + sn.storeId + "&catalogId=" + sn.catalogId + "&MyURL=" + encodeURIComponent("http://" + sn.domain + sn.context + "/tcd_" + sn.storeId + "_" + sn.catalogId + "_.html") : "https://" + sn.sslDomain + sn.context + "/SNUserRegisterView?storeId=" + sn.storeId + "&catalogId=" + sn.catalogId + "&MyURL=" + f
			} else if (-1 != window.location.href.indexOf("&krypto")) {
				var f = window.location.href.substring(window.location.href.lastIndexOf("/") + 1, window.location.href.indexOf("&krypto"));
				a = -1 != f.indexOf("LogonForm") || -1 != f.indexOf("SNUserRegisterView") || -1 != f.indexOf("ForgotPasswordView") || -1 != f.indexOf("SNUserRegisterView") || -1 != f.indexOf("ForgotPasswordCheckMail") || -1 != f.indexOf("ForgotPasswordSendMailView") || -1 != f.indexOf("ChangeCardPwdWithIdCard") ? "https://" + sn.sslDomain + sn.context + "/SNUserRegisterView?storeId=" + sn.storeId + "&catalogId=" + sn.catalogId + "&MyURL=" + encodeURIComponent("http://" + sn.domain + sn.context + "/tcd_" + sn.storeId + "_" + sn.catalogId + "_.html") : "https://" + sn.sslDomain + sn.context + "/SNUserRegisterView?storeId=" + sn.storeId + "&catalogId=" + sn.catalogId + "&MyURL=" + encodeURIComponent(window.location.href.substring(0, window.location.href.indexOf("&krypto")))
			} else {
				var g = window.location.href.substring(window.location.href.lastIndexOf("/") + 1, window.location.href.length);
				a = -1 != g.indexOf("LogonForm") || -1 != g.indexOf("SNUserRegisterView") || -1 != g.indexOf("ForgotPasswordView") || -1 != g.indexOf("SNUserRegisterView") || -1 != g.indexOf("ForgotPasswordCheckMail") || -1 != g.indexOf("ForgotPasswordSendMailView") || -1 != g.indexOf("ChangeCardPwdWithIdCard") ? "https://" + sn.sslDomain + sn.context + "/SNUserRegisterView?storeId=" + sn.storeId + "&catalogId=" + sn.catalogId + "&MyURL=" + encodeURIComponent("http://" + sn.domain + sn.context + "/tcd_" + sn.storeId + "_" + sn.catalogId + "_.html") : "https://" + sn.sslDomain + sn.context + "/SNUserRegisterView?storeId=" + sn.storeId + "&catalogId=" + sn.catalogId + "&MyURL=" + encodeURIComponent(window.location.href)
			}
			hrefLink(a)
		},
		q = function(c) {
			var d = k("cityId"),
				e = k("SN_CITY");
			if (d) "function" == typeof c && c(d);
			else if (e) {
				var f = r(e);
				"function" == typeof c && c(f.cityCommerceId)
			} else {
				var g = /^(\w*)(pre)(\w*)(.cnsuning.com)$/,
					h = /^(\w*)(sit)(\w*)(.cnsuning.com)$/,
					i = /^(\w*)(dev)(\w*)(.cnsuning.com)$/,
					j = document.location.hostname,
					l = "";
				g.test(j) ? l = "" : h.test(j) ? l = "" : i.test(j) && (l = "");
				var m = l + "/ipQuery.do";
				a.ajax({
					type: "GET",
					url: m,
					cache: !0,
					async: !1,
					dataType: "jsonp",
					jsonpCallback: "cookieCallback",
					success: function(a) {
						d = a.cityCommerceId, a.flag = "2", a.count = 0;
						var e = s(a);
						b("SN_CITY", e), b("cityId", a.cityCommerceId), b("districtId", a.districtCommerceId), "function" == typeof c && c(d)
					},
					error: function() {
						d = "9173", "function" == typeof c && c(d)
					}
				})
			}
		},
		r = function(a) {
			var b = a.split("|"),
				c = null;
			if (b.length > 0) {
				var d = b[0].split("_");
				c = {}, c.provinceMDMId = d[0], c.provinceCommerceId = d[1], c.cityMDMId = d[2], c.cityCommerceId = d[3], c.districtMDMId = d[4], c.districtCommerceId = d[5], c.flag = d[6], c.count = d[7]
			}
			return c
		},
		s = function(a) {
			var b = "";
			return b += a.provinceMDMId, b += "_", b += a.cityLESId, b += "_", b += a.cityMDMId, b += "_", b += a.cityCommerceId, b += "_", b += a.districtLESId, b += "_", b += a.districtCommerceId, b += "_", b += a.flag, b += "_", b += a.count
		},
		t = function() {
			var b = {
					contents: null,
					align: "right",
					vertical: "middle",
					zIndex: 7500,
					css: {},
					id: null,
					ieFixed: !0
				},
				c = a.browser.msie ? parseInt(a.browser.version) : !1;
			if (arguments.length < 1 || !(arguments[0] instanceof Object)) return a.error("ECode.floatBar: 参数必须为JSON对象");
			a.extend(b, arguments[0]);
			var d = {
				position: "fixed",
				top: "-9999em",
				left: "-9999em"
			};
			c && 6 >= c && (d.position = "absolute"), a('<div class="ECode-floatBar"></div>').css(d).appendTo("body");
			var e = a("body").find(".ECode-floatBar:last");
			e.append(b.contents);
			var f = e.width(),
				g = e.height(),
				h = {
					zIndex: b.zIndex
				};
			switch (null != b.id && e.attr("id", b.id), b.align) {
				case "right":
					h.left = "auto", h.right = 0;
					break;
				case "left":
					h.right = "auto", h.left = 0;
					break;
				case "center":
					h.right = "auto", h.left = "50%", h.marginLeft = -f / 2
			}
			switch (b.vertical) {
				case "top":
					h.top = 0;
					break;
				case "bottom":
					h.top = "auto", h.bottom = 0;
					break;
				case "middle":
					h.top = "50%", h.marginTop = -g / 2, c && 6 >= c && (h.marginTop = 0)
			}
			e.css(a.extend(h, b.css));
			var i = function() {
				var c = a(document).scrollTop(),
					d = a(window).height();
				a(document).width();
				switch (b.vertical) {
					case "top":
						e.stop().animate({
							top: c
						});
						break;
					case "bottom":
						var f = d + c - g;
						if ("undefined" != typeof b.css.marginBottom && null != b.css.marginBottom) {
							var h = parseInt(b.css.marginBottom);
							h >= 0 && (f -= h)
						}
						e.css({
							marginTop: 0
						}).stop().animate({
							top: f
						});
						break;
					case "middle":
						e.stop().animate({
							top: d / 2 + c - g / 2
						})
				}
			};
			b.ieFixed && c && 6 >= c && (i(), a(window).scroll(function() {
				i()
			}), a(window).resize(function() {
				i()
			}))
		},
		u = function(b) {
			var e = a(b);
			null != e && e.length > 0 && (e.live("mouseover", function() {
				c(this)
			}), e.click(function() {
				d(this)
			}))
		};
	screen.width < 990 ? smallScreen = !1 : smallScreen = !1;
	var v, w, x = document.location.hostname;
	switch (i(x)) {
		case "pre":
			v = "pre.cn", w = "pre";
			break;
		case "sit":
			v = "sit.cn", w = "sit1";
			break;
		case "prd":
			v = ".", w = "";
			break;
		default:
			v = "pre.cn"
	}
	if ("https" == f) var y = new Date,
		z = y.getFullYear() + "" + y.getMonth() + y.getDate(),
		A = {
			topNav: "https://" + w + "imgssl.suning.com/images/nav.html?v=" + z,
			allSort: "https://" + w + "imgssl.suning.com/images/cate.html?v=" + z,
			mainNav: "https://" + w + "imgssl.suning.com/images/chn.html?v=" + z,
			threeData: "https://" + w + "imgssl.suning.com/images/menuData.html?v=" + z
		};
	else if ("http" == f) var A = {
		topNav: "http://lib" + v + "suning.com/header/nav-topnav.jsonp",
		allSort: "http://lib" + v + "suning.com/header/cate-allSort.jsonp",
		mainNav: "http://lib" + v + "suning.com/header/chn-mainNav.jsonp",
		threeData: "http://lib" + v + "suning.com/header/menuData-threeSortShow.jsonp"
	};
	if (!g) {
		var B, C = (window.location + "", new RegExp(/Pad/) || new RegExp(/pad/));
		B = !!C.exec(navigator.userAgent)
	}
	var D = function() {
			B && (a("a.touch-href").attr("href", "javascript:void(0);"), a(".ng-sort").find("ul.sort-list").find("a").attr("href", "javascript:void(0);"), a(".ng-sort").find("a.ng-all-hook").attr("href", "javascript:void(0);"), a(".ng-bar-node-mini-cart").attr("href", "javascript:void(0);"))
		},
		E = function() {
			var b, c = a(".app-down-box"),
				d = c.find(".ng-d-box"),
				e = c.find("img[src3]"),
				f = function() {
					c.find(".ng-bar-node").addClass("ng-bar-node-hover"), e.each(function() {
						a(this).attr("src", a(this).attr("src3")).removeAttr("src3")
					}), d.slideDown(100)
				},
				g = function() {
					c.find(".ng-bar-node").removeClass("ng-bar-node-hover"), d.slideUp(100)
				};
			c.hover(function() {
				clearTimeout(b), b = setTimeout(function() {
					f()
				}, 150)
			}, function() {
				clearTimeout(b), b = setTimeout(function() {
					g()
				}, 200)
			}), c.find("a.ng-bar-node").click(function() {
				alert();
				a(this).toggleClass("ng-bar-node-hover").siblings(".ng-d-box").slideToggle(100)
			}), a(".ng-site-nav-box").hover(function() {
				var b = a(this).position().left;
				a(".ng-sn-site-nav").css("left", -b), SFE.search.clearBox(), SFE.search.searchIptBlur()
			}), cartHandle = a(".ng-bar-node-mini-cart"), a(".ng-sn-site-nav").find("i.new").length >= 1 && a(".ng-site-nav-box").find("a.ng-bar-node").find("i.new").css("display", "inline-block")
		},
		F = function() {
			var b = a(".ng-gif-logo img , img.slogn"),
				c = b.attr("src3");
			b.attr("src", c)
		},
		G = function(b) {
			var c, b = a(b);
			b.hover(function() {
				var b = a(this);
				clearTimeout(c), c = setTimeout(function() {
					b.find("a.ng-bar-node").addClass("ng-bar-node-hover").siblings(".ng-d-box").slideDown(100)
				}, 150)
			}, function() {
				var b = a(this);
				clearTimeout(c), c = setTimeout(function() {
					b.find("a.ng-bar-node").removeClass("ng-bar-node-hover").siblings(".ng-d-box").slideUp(100)
				}, 150)
			}), b.find("a.ng-bar-node").hover(function() {
				a(this).toggleClass("ng-bar-node-hover").siblings(".ng-d-box").slideToggle(100)
			})
		},
		H = function() {
			SFE.base.miniCartNum(), window.SnSidebar && SnSidebar._getCartNum()
		},
		I = function() {
			var b = k("totalProdQty");
			b = 0 == b || null == b ? 0 : b, b = b > 99 ? "99+" : b, a("#showTotalQty").html(b);
			var c = a(".ng-bar-node-mini-cart").find("em.cart");
			0 == b || null == b ? c.html("&#xe623;") : c.html("&#xe624;")
		},
		J = function() {
			var b = (a(".ng-site-nav-box"), a(".ng-sort-list-box"), a(".ng-nav-index").find(".ng-nav"), a(".ng-nav-right-txtact")),
				c = k("idsLoginUserIdLastTime");
			null != c && "" != c || a.ajax({
				url: A.mainNav,
				method: "get",
				dataType: "jsonp",
				jsonpCallback: "mainNav",
				cache: !0,
				success: function(a) {
					b.html(a)
				}
			})
		},
		K = function() {
			a(".ng-toolbar").find("a.ng-close").click(function() {
				var b = a(this).parents(".ng-bar-node-box");
				b.find(".ng-d-box").slideUp(100, function() {
					b.find(".ng-bar-node").removeClass("ng-bar-node-hover")
				})
			})
		},
		L = function() {
			var b = k("logonStatus");
			if (null != b && "" != b) {
				var c = k("nick");
				return null == c && (c = ""), c.length > 12 && (c = c.substr(0, 12)), a("#username-node-slide").show().find("a.username-bar-node-noside").show().find("span").html(c), a(".reg-bar-node").hide(), SFE.base.miniCartNum(), !0
			}
			return a(".username-bar-node").hide().find("span").html(""), a(".reg-bar-node").show(), SFE.base.miniCartNum(), !1
		},
		M = function() {
			function b(a) {
				var b;
				if (isNaN(a) || void 0 == a || null == a) b = "";
				else {
					var c = parseInt(a);
					c = c > 99 ? "99+" : c, b = "(" + c + ")"
				}
				return b
			}
			if (L()) {
				var c = a("#waitEvaluation"),
					d = a("#waitDeliveryCounts"),
					e = a("#waitPayCounts"),
					g = !1,
					h = !1;
				a(".myorder-handle").mouseenter(function() {
					if (!g) {
						k("custno");
						a.ajax({
							url: f + "://review" + v + "suning.com/ajax/getpendingCount/waitEvaluation_callback.do",
							method: "get",
							dataType: "jsonp",
							cache: !0,
							jsonpCallback: "waitEvaluation_callback",
							success: function(a) {
								var d = parseInt(a.pendingOrderCount);
								c.html(b(d)), g = !0
							}
						})
					}
					h || a.ajax({
						url: f + "://member" + v + "suning.com/webapp/wcs/stores/servlet/SNOrdersCountCmd",
						method: "get",
						dataType: "jsonp",
						success: function(a) {
							d.html(b(a.waitDeliveryCounts)), e.html(b(a.waitPayCounts)), h = !0
						}
					})
				})
			}
		},
		N = function() {
			function b() {
				var a, b, c, d, e = 0;
				i.find("li").live({
					mouseenter: function(c) {
						a = c.pageX, b = c.pageY, g = 1 == e ? 0 : 300
					},
					mouseleave: function(f) {
						c = f.pageX, d = f.pageY, e = a + 5 >= c ? Math.abs(d - b) <= 28 ? 0 : 1 : 0
					}
				}), i.live("mouseleave", function() {
					e = 0
				})
			}

			function c() {
				j.animate({
					width: "0px"
				}, 100, function() {
					i.find("li").removeClass("hover"), a(this).removeClass("ng-sort-detail-border")
				}), m.mouseleave()
			}

			function d() {
				q || a.ajax({
					url: A.threeData,
					method: "get",
					dataType: "jsonp",
					jsonpCallback: "threeSortShow",
					cache: !0,
					success: function(a) {
						p = a, q = !0
					}
				})
			}

			function e(b) {
				var c = a(this).scrollTop(),
					d = i.offset().top;
				sn.isHome && (c > d ? j.animate({
					top: c - d + 38
				}, 100) : j.animate({
					top: 38
				}, 100));
				var e = "",
					f = "";
				if (r.html(" "), s.html(" "), q && "undefined" != typeof p && "undefined" != typeof p[b]) {
					var g = k("cityId") || "9173",
						h = p[b];
					if ("undefined" != typeof h.channel)
						for (var l = 0; l < h.channel.length; l++) {
							channelData = h.channel[l];
							var m = null == channelData.link.match(/cityId=.*&/gi) ? "" : "&";
							e += "<a href='" + channelData.link.replace(/cityId=.*?&|cityId=.*$/gi, "cityId=" + g + m) + "' onclick='SFE.base.replaceCityPlaceHolder(this);' name='" + channelData.trickPoint + "' target='_blank' style='background-color:" + channelData.style + "'>" + channelData.title + "</a>", r.html(e)
						}
					if (sn.isNewHome)
						if (0 == j.find("img").length) {
							for (var n = " ", l = 0; l < p.length; l++) {
								var o = p[l].p;
								n += "undefined" != typeof o && "undefined" != typeof o.link ? "<a class='threeListAct' href ='" + o.link + "' target='_blank' title='" + o.title + "' name='" + o.trickPoint + "'><img src='" + o.picUrl + "' alt='" + o.title + "' /></a>" : "<a class='threeListAct threeListAct-nopic' href ='#' target='_blank' title='#' name='#'><img src='#' alt='#' /></a>"
							}
							j.append(n);
							var t = j.find("a.threeListAct").eq(b);
							t.siblings("a.threeListAct").hide(), t.hasClass("threeListAct-nopic") || t.css("display", "block")
						} else {
							var t = j.find("a.threeListAct").eq(b);
							t.siblings("a.threeListAct").hide(), t.hasClass("threeListAct-nopic") || t.css("display", "block")
						}
					if ("undefined" != typeof h.sub)
						for (var l = 0; l < h.sub.length; l++) {
							var u = h.sub[l],
								v = 0 == l ? "lastdl" : "";
							if (f += "<dl class='" + v + "'>", "undefined" != typeof u.t) {
								var w = u.t.title,
									x = u.t.link,
									y = u.t.trickPoint,
									z = u.t.style,
									m = null == x.match(/cityId=.*&/gi) ? "" : "&";
								f += "<dt><a href='" + x.replace(/cityId=.*?&|cityId=.*$/gi, "cityId=" + g + m) + "' onclick='SFE.base.replaceCityPlaceHolder(this);'' name='" + y + "' class='" + z + "' target='_blank'>" + w + "</a></dt>"
							}
							if ("undefined" != typeof u.s && u.s.length > 0) {
								f += "<dd>";
								for (var A = 0; A < u.s.length; A++) {
									var B = u.s[A],
										C = B.title,
										D = B.link,
										E = B.trickPoint,
										F = B.style,
										m = null == D.match(/cityId=.*&/gi) ? "" : "&";
									f += "<a href='" + D.replace(/cityId=.*?&|cityId=.*$/gi, "cityId=" + g + m) + "' onclick='SFE.base.replaceCityPlaceHolder(this);'' name='" + E + "' class='" + F + "' target='_blank'>" + C + "</a>"
								}
								f += "</dd>"
							}
							f += "</dl>", s.html(f)
						}
				}
			}
			var f, g, h, i = a(".ng-sort-list-box"),
				j = a(".ng-sort-detail"),
				l = a("a.ng-all-hook"),
				m = a(".ng-sort"),
				n = a(".ng-nav-index");
			b(), i.find("li").live({
				mouseenter: function() {
					var b = a(this);
					clearTimeout(f), f = setTimeout(function() {
						b.addClass("hover").siblings("li").removeClass("hover");
						var a = b.index(),
							c = b.attr("maxCol");
						c = c > 7 || 0 == c || null == c ? 7 : c, h = 100 * c + 20 + "px", e(a), !j.find("a.threeListAct").eq(a).hasClass("threeListAct-nopic") && sn.isNewHome ? j.css("width", 800).addClass("ng-sort-detail-border") : j.css("width", 640).addClass("ng-sort-detail-border")
					}, g)
				},
				mouseleave: function() {
					clearTimeout(f)
				}
			});
			var o;
			i.hover(function() {
				clearTimeout(o), o = setTimeout(function() {
					SFE.search.clearBox(), SFE.search.searchIptBlur()
				}, 200)
			}, function() {
				clearTimeout(o), o = setTimeout(function() {
					c()
				}, 200)
			}), j.find("a.ng-close-sort").click(function() {
				c(), smallScreen && l.click()
			}), smallScreen && (l.attr("href", "javascript:void(0);").find("span").css("text-decoration", "none"), l.toggle(function() {
				i.slideDown(function() {
					sn.isHome && n.animate({
						width: "90px"
					}, 200)
				})
			}, function() {
				sn.isHome ? n.animate({
					width: "0px"
				}, 200, function() {
					i.slideUp()
				}) : i.slideUp()
			}), m.click(function(a) {
				a.stopPropagation()
			}), a(document).click(function() {
				smallScreen && i.is(":visible") && l.click()
			}));
			var p, q = !1,
				r = a(".sort-chanel"),
				s = a(".cate-list");
			if (sn.isHome) d();
			else {
				var g;
				l.mouseover(function() {
					clearTimeout(g), g = setTimeout(function() {
						d()
					}, 200)
				})
			}
		},
		O = function() {
			function b() {
				i = a(window).scrollTop(), l = a(document).height() - q - 100, q = a(window).height();
				var b = sn.isHome ? 330 : 0;
				0 == j ? k = n.offset().top + p + b : "", q > 660 && !h && (sn.isHome || sn.hasTopFixed) && (i > k ? c() : d(), j = i > k), k >= i && (d(), j = !1), 0 == j ? "" : SFE.search.clearBox()
			}

			function c() {
				o.fadeIn(0), smallScreen && sn.isHome ? "" : n.addClass("ng-sort-fixed"), sn.isHome ? n.removeClass("ng-sort-index") : "", smallScreen ? "" : n.find(".ng-sort-list-box").hide(), a(".ng-bar-node-mini-cart").addClass("ng-bar-node-mini-cart-fixed"), a(".reg-bar-node , #username-node-slide ,#username-node").addClass("reg-bar-node-fixed"), a(".ng-search").find(".g-search").addClass("g-search-fixed"), a(".ng-nav-bar").addClass("ng-nav-bar-fixed"), a(".ng-nav-index").hide()
			}

			function d() {
				n.removeClass("ng-sort-fixed"), sn.isHome ? n.addClass("ng-sort-index") : "", sn.isHome && !smallScreen ? n.find(".ng-sort-list-box").show() : "", a(".ng-bar-node-mini-cart").removeClass("ng-bar-node-mini-cart-fixed"), a(".reg-bar-node , #username-node-slide ,#username-node").removeClass("reg-bar-node-fixed"), a(".ng-search").find(".g-search").removeClass("g-search-fixed"), a(".ng-nav-bar").removeClass("ng-nav-bar-fixed"), a(".ng-nav-index").show(), o.fadeOut(100)
			}

			function e() {
				0 == r.find("ul.sort-list").length && a.ajax({
					url: A.allSort,
					method: "get",
					dataType: "jsonp",
					jsonpCallback: "allSort",
					cache: !0,
					success: function(a) {
						r.prepend(a)
					}
				})
			}

			function f() {
				q > 500 && (t.stop(!1, !0).slideDown(), t.find("img[src3]").each(function() {
					a(this).attr("src", a(this).attr("src3")).removeAttr("src3")
				}), u.addClass("ng-btn-hover"))
			}

			function g() {
				t.stop(!1, !0).slideUp(), u.removeClass("ng-btn-hover")
			}
			var i, j, k, l, m, n = a(".ng-sort"),
				o = a(".ng-fix-bar"),
				p = n.height(),
				q = a(window).height(),
				r = (a(".ng-bottom-fixed-pub"), a(".ng-bottom-fixed-sidebar"), a(".ng-sort-list-box"));
			a(window).scroll(function() {
				b(), i > l ? f() : g()
			}), n.hover(function() {
				if (j || !sn.isHome) {
					clearTimeout(m);
					a(this);
					e(), m = setTimeout(function() {
						r.slideDown()
					}, 200)
				}
			}, function() {
				if (j || !sn.isHome) {
					clearTimeout(m);
					var b = a(this);
					m = setTimeout(function() {
						b.find(".ng-sort-detail").animate({
							width: "0px"
						}, 100, function() {
							r.slideUp(200)
						})
					}, 200)
				}
			});
			var s = a(".ng-bottom-fixed"),
				t = s.find(".ng-slide-box-code"),
				u = s.find("a.code-btn"),
				v = s.find("a.ng-btn"),
				w = a(".ng-slide-box-life"),
				x = s.find("a.ng-close");
			v.click(function() {
				s.find(".ng-slide-box").slideUp().siblings("a.ng-btn").removeClass("ng-btn-hover")
			});
			var y = u.attr("link");
			500 > q && u.attr({
				href: y,
				target: "_blank"
			}), sn.isHome ? "" : a("#ng-mob-link").attr("href", y), u.click(function() {
				t.is(":visible") ? g() : f()
			}), s.find(".life-help-btn").click(function() {
				a(this).toggleClass("ng-btn-hover"), w.is(":visible") ? w.slideUp() : w.slideDown()
			}), a(".ng-backtotop").click(function() {
				a("html, body").animate({
					scrollTop: 0
				}, 200)
			}), a(document).on("keyup", function(b) {
				var c = b.target.nodeName.toUpperCase();
				"INPUT" != c && "TEXTAREA" != c && 84 == b.which && a(".ng-backtotop").click()
			}), x.click(function() {
				a(this).parent(".ng-slide-box").slideUp(), s.find("a.ng-btn").removeClass("ng-btn-hover")
			}), a(document).click(function() {
				s.find(".ng-slide-box").slideUp(), v.removeClass("ng-btn-hover")
			}), s.click(function(a) {
				a.stopPropagation()
			})
		},
		P = function() {
			function b(b) {
				var c = a(b);
				return c.length > 0 ? a(window).scrollTop() + a(window).height() > c.offset().top && c.offset().top + c.height() > a(window).scrollTop() : void 0
			}

			function c() {
				var b = a(".ng-new-pro"),
					c = b.find(".footer-egg-btn"),
					d = b.find(".footer-egg-con"),
					f = '<div id="foot_canvas"></div><link href="http://sale.suning.com/images/advertise/helloworld/css/footer-egg-css.css?var=06" rel="stylesheet" /><script src="http://sale.suning.com/images/advertise/helloworld/js/footer-egg-js.js?var=06" type="text/javascript"></script>',
					g = a(window).width(),
					h = b.find(".ng-new-pro-con").width(),
					i = (g - h) / 2;
				c.css("width", i), c.click(function() {
					d.show().html(f), e = !0
				})
			}

			function d() {
				if (b(".ng-footer") && 0 != a(".footer-dom").length) {
					var d = a("#footer-dom-01").val(),
						f = a("#footer-dom-02").val();
					a("#footer-dom-01").remove(), a("#footer-dom-02").remove(), d = d ? d : "";
					var g = d + f;
					a(".ng-footer").prepend(g)
				}
				a(window).width() > 990 && !e && sn.isHome && c()
			}
			var e = !1;
			d(), a(window).resize(function() {
				d()
			}).scroll(function() {
				d()
			})
		},
		Q = function() {
			var b = i(document.location.hostname),
				c = "",
				d = {};
			L() && (c = "prd" == b ? "//msg.suning.com/mms-web/" : "//msg" + b + ".cnsuning.com/mms-web/", a.ajax({
				url: c + "service/getlastunreadmsg.do",
				method: "get",
				dataType: "jsonp",
				cache: !1,
				jsonpCallback: "getUnreadMsg",
				success: function(b) {
					b && b.status && b.status > 0 && (a(".ng-bar-node-msg .dot").show(), a(".ng-msg-child .ng-msg-list").html('<a class="ng-msg-item" name="public0_none_dbgjt_wdxx02" href="' + (b.msgUrl || "//msg.suning.com/") + '" target="_blank" unread="true"><i></i><span>' + b.msgInfo + "</span></a>"), d = b)
				}
			}), a(".ng-msg-child").on("click", ".ng-msg-item[unread]", function() {
				a(this).data();
				a.ajax({
					url: c + "service/updateMsgToreaded.do",
					method: "get",
					dataType: "jsonp",
					cache: !1,
					jsonpCallback: "updateUnreadMsg",
					data: {
						msgId: d.msgId,
						terminalCode: d.terminalCode,
						typeCode: d.msgTypeCode
					},
					success: function(b) {
						var c = "";
						b && 0 == b.returnCode && (a(".ng-bar-node-msg .dot").hide(), c = '<div class="ng-msg-item ng-msg-item-no"><i></i><span>嗷~ 没有新消息...</span></div>', a(".ng-msg-child .ng-msg-list").html(c))
					}
				})
			}))
		},
		R = function() {
			E(), G(".ng-site-nav-box"), G(".ng-msg-box"), G(".myorder-handle"), G(".mysuning-handle"), G(".service-handle"), G(".username-handle"), K(), D(), J(), M(), F(), Q()
		},
		S = !1,
		T = function() {
			var b = a("#searchKeywords"),
				c = a.trim(b.val());
			if ("" == c) b.focus();
			else {
				var d = a("#g_static_channel_name").val();
				if ("snbook" == d) {
					var f = sn.searchDomain.replace("emall/", "") + "web/search.do?keywords=" + encodeURIComponent(e(c));
					return window.location.href = f, !1
				}
				var f = sn.searchDomain.replace("emall/", "") + encodeURIComponent(e(c)),
					g = k("cityId") || "9173";
				f += "/cityId=" + g, "22001" == sn.searchCatalogId && (f = sn.searchDomain + "bookSearch.do?keyword=" + encodeURIComponent(c), f += "&cityId=" + g, a("#bookSearchChannel").length > 0 && (f += a("#bookSearchChannel").attr("value"))), "14655" == sn.searchCatalogId && (f += "&ch=1"), "14656" == sn.searchCatalogId && (f += "&ch=2"), "undefined" != typeof searchCatalogId && "" != searchCatalogId && 0 != searchCatalogId && (f += "&ci=" + searchCatalogId), S && (f = sn.searchDomain.replace("emall/", "") + "shop/search.do?app=shopsearch&keyword=" + encodeURIComponent(c)), "undefined" != typeof param && ("10" == param.searchType ? f += "&ch=1" : "12" == param.searchType && (f += "&ch=2"));
				try {
					var h = a(".g-ac-store").find("em").eq(0).text(),
						i = c,
						j = "YT_" + i + "_" + h + "_" + search_da_djc_index,
						l = a('<a href="###" name="' + j + '"></a>')[0];
					"undefined" != typeof sa && "undefined" != typeof sa.click && sa.click.sendDatasIndex(l)
				} catch (m) {}
				window.location.href = f
			}
			return !1
		},
		U = {},
		V = function() {
			if (0 == a(".g-search").length || h || sn.noShowTopCms) return !1;
			switch (i(x)) {
				case "prd":
					U = {
						domains: "http://cms.api.suning.com/",
						imgdomains: "http://image.suning.cn/"
					};
					break;
				case "pre":
					U = {
						domains: "http://cmspre.api.cnsuning.com/",
						imgdomains: "http://uimgpre.cnsuning.com/"
					};
					break;
				case "sit":
					U = {
						domains: "http://cmssit.api.cnsuning.com/",
						imgdomains: "http://uimgpre.cnsuning.com/"
					};
					break;
				case "sit2":
					U = {
						domains: "http://cmssit.api.cnsuning.com/",
						imgdomains: "http://uimgpre.cnsuning.com/"
					}
			}
			var b = U.domains + "activityNav-SFE.base.activityNavHtml.jsonp";
			a.ajax({
				type: "get",
				cache: !0,
				dataType: "jsonp",
				url: b,
				jsonpCallback: "SFE.base.activityNavHtml",
				success: function(a) {},
				error: function() {}
			})
		},
		W = function(b) {
			if ("undefined" != typeof b && b && "undefined" != b) {
				var c, d, e = b.activityNavImg.tag,
					f = b.activityNavBtn.tag,
					g = b.navLiftList.tag,
					h = b.navRightList.tag,
					i = b.actNavCode.tag,
					j = b.activityNavBg.tag,
					k = b.actFooterTitle.tag,
					l = "",
					m = "",
					n = "";
				if (e && f && j && e.length && f.length && j.length) {
					c = e[0].linkUrl ? '<a href="' + e[0].linkUrl + '" target="_blank" ' : '<a href="javascript:;"', l = '<div class="activity-nav-wrapper" style=" background:' + j[0].color + ';"><div class="activity-nav">' + c + '" title="' + e[0].elementName + '"><img src="' + U.imgdomains + e[0].picUrl + '" alt="" width="140" height="55" /></a><ul>';
					for (var o = 0; o < f.length; o++) n = f[o].elementName.length > 3 ? "fouthword" : "",
						c = f[o].linkUrl ? '<a href="' + f[o].linkUrl + '" target="_blank" name=:"' + f[o].trickPoint + '"' : '<a href="javascript:;"', l += "<li>" + c + '" class="' + n + '">' + f[o].elementName + '</a><i class="angle"></i></li>';
					l += "</ul></div></div>", a(".ng-toolbar").before(l)
				}
				if ((a(".ng-footer").find(".ng-ser-box").length > 0 || a(".ng-footer").find(".footer-dom").length > 1) && g && h && i && k && g.length && h.length && i.length && k.length) {
					var p = k[0].elementDesc.split(";"),
						q = p[0] ? p[0] : "",
						r = p[1] ? p[1] : "";
					c = k[0].linkUrl ? '<a href="' + k[0].linkUrl + '" target="_blank" name="' + k[0].trickPoint + '"' : '<a href="javascript:;"', d = k[1].linkUrl ? '<a href="' + k[1].linkUrl + '" target="_blank" name="' + k[1].trickPoint + '"' : '<a href="javascript:;"', m = '<div class="activity-list-wrapper" style="background:' + q + '"><div class="activity-title"><h3 class="main-enter">' + c + ' style="color:' + k[0].color + ';">' + k[0].elementName + '</a><span></span></h3><h3 class="activity-enter">' + d + ' style="color:' + k[0].color + ';">' + k[1].elementName + '</a><span></span></h3></div><div class="activity-list"><div class="mobiledown"><div class="code-wrapper" style="background:' + r + '"><div class="code"><img src="' + U.imgdomains + i[0].picUrl + '" alt="" width="75" height="75" /></div><p>' + i[0].elementName + '</p></div><p class="title" style="color:' + i[0].color + '">' + i[0].elementDesc + '</p></div><ul class="activity-list-left">';
					for (var s = 0; s < g.length; s++) c = g[s].linkUrl ? '<a href="' + g[s].linkUrl + '" target="_blank" name="' + g[s].trickPoint + '"' : '<a href="javascript:;"', m += '<li style="background:' + r + ';">' + c + "><span>" + g[s].elementName + "</span><i>></i></a></li>";
					m += '</ul><ul class="activity-list-right">';
					for (var t = 0; t < h.length; t++) c = h[t].linkUrl ? '<a href="' + h[t].linkUrl + '" target="_blank" name="' + h[t].trickPoint + '"' : '<a href="javascript:;"', m += '<li style="background:' + r + ';">' + c + "><span>" + h[t].elementName + "</span><i>></i></a></li>";
					m += "</ul></div></div>", a(".ng-footer").before(m)
				}
			}
		};
	return {
		d: k,
		toolBarEvent: R,
		setSearchCity: u,
		replaceCityParam: c,
		replaceCityPlaceHolder: d,
		registerurl: p,
		logonurl: o,
		allSort: N,
		fixEvent: O,
		miniCartReload: H,
		miniCartNum: I,
		isLogin: L,
		getCity: q,
		logoff: n,
		footerLazyLoad: P,
		floatBar: t,
		onSubmitSearch: T,
		getActivityNav: V,
		activityNavHtml: W
	}
}(jQuery), $(function() {
	SFE.base.toolBarEvent(), SFE.base.getActivityNav(), SFE.search.searchEvent(), SFE.base.allSort(), SFE.base.fixEvent(), SFE.base.footerLazyLoad(), $("a[name^=public0_],input[name^=public0_]").live("click", function() {
		"undefined" != typeof sa && sa.click.sendDatasIndex(this)
	}), $(".ng-bottom-fixed a.ng-btn").on("click", function() {
		"undefined" != typeof sa && sa.click.sendDatasIndex(this)
	})
});