KISSY.use("ua, core", function (a, b) {
  function c() {
    return i
      ? i
      : (a.ready(function () {
          a.use("node", function (a, b) {
            i = b;
          });
        }),
        null);
  }
  function d() {
    var b = this;
    a.mix(b, h.Target),
      (b.navigationsData = null),
      (b.fetchData = function () {
        var c = setTimeout(function () {
            o.data.navigations;
            b.refresh(o.data);
          }, 1500),
          d = f + "/my_taobao_api/getLeftNavigation.json";
        new a.IO({
          url: d,
          dataType: "jsonp",
          scriptCharset: "utf-8",
          timeout: 5e3,
          success: function (a) {
            return 0 !== a.status
              ? void b.fire("fetchDataFailed")
              : (clearTimeout(c), void b.refresh(a.data));
          },
          error: function () {
            b.fire("fetchDataFailed");
          },
        });
      }),
      (b.changeFoState = function (b, c) {
        var d = k[b];
        if (d) {
          var e = f + "/my_taobao_api/putLeftNavigation.json";
          new a.IO({
            url: e,
            dataType: "jsonp",
            scriptCharset: "utf-8",
            data: { leftStatus: d, leftStatusType: c },
            success: function (a) {
              0 !== a.status;
            },
          });
        }
      }),
      (b.save = function (c) {
        var d = f + "/my_taobao_api/putUncheckedNavigation.json",
          e = [];
        a.each(c, function (b, c) {
          var d = [];
          a.each(b, function (a, b) {
            a || d.push(b);
          }),
            d.length && e.push(c + ":" + d.join(","));
        }),
          new a.IO({
            url: d,
            dataType: "jsonp",
            scriptCharset: "utf-8",
            data: { unCheckNa: e.join(";") },
            success: function (a) {
              return 0 !== a.status
                ? void b.fire("saveFailed")
                : void b.fire("saveDone");
            },
            error: function () {
              b.fire("saveFailed");
            },
          });
      }),
      (b.refresh = function (a) {
        (b.navigationsData = a), b.fire("refresh");
      }),
      (b.getData = function () {
        return b.navigationsData;
      });
  }
  var e;
  (e = "undefined" == typeof __MT_MENU_FLAGS ? {} : __MT_MENU_FLAGS),
    a.namespace("MTB", !0),
    (MTB = { _version: "3.0", _description: "MyTaobao Namespace" });
  var f;
  f =
    location.host.indexOf("i.daily.taobao.net") > -1
      ? "//i.daily.taobao.net"
      : "//i.taobao.com";
  var a = KISSY,
    g = a.DOM,
    h = a.Event,
    i = null,
    j = new d(),
    k = { 201: 1, 503: 2 },
    l = { 201: "businessStatus", 503: "recentVisitStatus" };
  c();
  try {
    (g.get("#J_ITouchDomain") || g.get("#J_quanzi")) &&
      (document.domain =
        location.host.indexOf("daily") > -1 ? "taobao.net" : "taobao.com");
  } catch (m) {}
  var n = {
      _getSearchURL: function (a) {
        switch (a) {
          case "shop":
            return "//shopsearch.taobao.com/search?initiative_id=staobaoz_20120831&spm=a1z02.1.6856637.d4910789&stat=40&shopf=newsearch&q=";
          case "item":
            return "//s.taobao.com/search?spm=a1z02.1.6856637.d4910789&q=";
        }
      },
      _searchForm: function () {
        return g.get("#J_TSearchForm");
      },
    },
    o = {
      data: {
        businessStatus: 1,
        navigations: [
          {
            htmlId: "",
            name: "\u8d2d\u7269",
            navigationId: 100,
            order: 100,
            status: 0,
            subNavigations: [
              {
                htmlId: "htmlId",
                name: "\u6211\u7684\u8d2d\u7269\u8f66",
                navigationId: 101,
                order: 101,
                parentId: 0,
                spm: "a1z02.1.a2109.d1000367.7bdUMD",
                status: 0,
                subNavigations: [],
                url: "//cart.taobao.com/cart.htm",
              },
              {
                htmlId: "htmlId",
                name: "\u6211\u7684\u8db3\u8ff9",
                navigationId: 102,
                order: 102,
                parentId: 0,
                spm: "a1z02.1.a2109.d1000391.7bdUMD",
                status: 0,
                subNavigations: [],
                url: "//lu.taobao.com/newMyPath.htm",
              },
              {
                htmlId: "htmlId",
                name: "\u6211\u7684\u8bc4\u4ef7",
                navigationId: 103,
                order: 103,
                parentId: 0,
                spm: "a1z02.1.a2109.d1000377.7bdUMD",
                status: 0,
                subNavigations: [],
                url: "//rate.taobao.com/myRate.htm",
              },
            ],
            url: "",
          },
          {
            htmlId: "",
            name: "\u8ba2\u5355",
            navigationId: 200,
            order: 200,
            status: 0,
            subNavigations: [
              {
                htmlId: "htmlId",
                name: "\u5df2\u4e70\u5230\u5b9d\u8d1d",
                navigationId: 201,
                order: 201,
                parentId: 0,
                spm: "a1z02.1.a2109.d1000368.7bdUMD",
                status: 0,
                subNavigations: [
                  {
                    htmlId: "htmlId",
                    name: "\u6211\u7684\u62cd\u5356",
                    navigationId: 202,
                    order: 202,
                    parentId: 201,
                    spm: "a1z02.1.a2109.d1000369.7bdUMD",
                    status: 0,
                    subNavigations: [],
                    url: "//paimai.taobao.com/auctionList/my_auction_list.htm",
                  },
                  {
                    htmlId: "htmlId",
                    name: "\u673a\u7968\u9152\u5e97\u4fdd\u9669",
                    navigationId: 203,
                    order: 203,
                    parentId: 201,
                    spm: "a1z02.1.a2109.d1000370.7bdUMD",
                    status: 0,
                    subNavigations: [],
                    url: "//jipiao.trip.taobao.com/order_manager.htm",
                  },
                  {
                    htmlId: "htmlId",
                    name: "\u6211\u7684\u5f69\u7968",
                    navigationId: 204,
                    order: 204,
                    parentId: 201,
                    spm: "a1z02.1.a2109.d1000371.7bdUMD",
                    status: 0,
                    subNavigations: [],
                    url: "//caipiao.taobao.com/lottery/order/my_all_lottery_order.htm",
                  },
                ],
                url: "//buyertrade.taobao.com/trade/itemlist/list_bought_items.htm",
              },
            ],
            url: "",
          },
          {
            htmlId: "",
            name: "\u4f18\u60e0",
            navigationId: 300,
            order: 300,
            status: 0,
            subNavigations: [
              {
                htmlId: "htmlId",
                name: "\u6211\u7684\u4f18\u60e0\u4fe1\u606f",
                navigationId: 301,
                order: 301,
                parentId: 0,
                spm: "a1z02.1.a2109.d1000376.h4qhap",
                status: 0,
                subNavigations: [],
                url: "//marketingop.taobao.com/cashHongbao.htm",
              },
              {
                htmlId: "htmlId",
                name: "\u5929\u732b\u79ef\u5206",
                navigationId: 302,
                order: 302,
                parentId: 0,
                spm: "a1z02.1.972272805.d4912025.an1eGf",
                status: 0,
                subNavigations: [],
                url: "//vip.tmall.com/vip/index.htm",
              },
              {
                htmlId: "htmlId",
                name: "\u5929\u732b\u5361\u5377",
                navigationId: 303,
                order: 303,
                parentId: 0,
                spm: "a1z02.1.972272805.d4912029.an1eGf",
                status: 0,
                subNavigations: [],
                url: "//trade.tmall.com/member/myCoupon.htm",
              },
            ],
            url: "",
          },
          {
            htmlId: "",
            name: "\u9000\u6b3e\u7ef4\u6743",
            navigationId: 400,
            order: 400,
            status: 0,
            subNavigations: [
              {
                htmlId: "htmlId",
                name: "\u9000\u6b3e\u7ba1\u7406",
                navigationId: 401,
                order: 401,
                parentId: 0,
                spm: "a1z02.1.a2109.d1000379.h4qhap",
                status: 0,
                subNavigations: [
                  {
                    htmlId: "htmlId",
                    name: "\u552e\u540e\u7ba1\u7406",
                    navigationId: 402,
                    order: 402,
                    parentId: 401,
                    spm: "a1z02.1.a2109.d1000380.h4qhap",
                    status: 0,
                    subNavigations: [],
                    url: "//support.taobao.com/myservice/aftersales/buyer_rights_list.htm?nekot=1410939138028",
                  },
                  {
                    htmlId: "htmlId",
                    name: "\u6295\u8bc9\u7ba1\u7406",
                    navigationId: 403,
                    order: 403,
                    parentId: 401,
                    spm: "a1z02.1.a2109.d1000383.h4qhap",
                    status: 0,
                    subNavigations: [],
                    url: "//support.taobao.com/myservice/rules/buyer_rules_list.htm?nekot=1410939138028",
                  },
                  {
                    htmlId: "htmlId",
                    name: "\u4e3e\u62a5\u7ba1\u7406",
                    navigationId: 404,
                    order: 404,
                    parentId: 401,
                    spm: "a1z02.1.a2109.d1000381.h4qhap",
                    status: 0,
                    subNavigations: [],
                    url: "//archer.taobao.com/myservice/report/report_i_posted_list.htm?type=2&user_role=2&isarchive=false&nekot=1410939138028",
                  },
                  {
                    htmlId: "htmlId",
                    name: "\u54a8\u8be2\u56de\u590d",
                    navigationId: 405,
                    order: 405,
                    parentId: 401,
                    spm: "a1z02.1.a2109.d1000382.h4qhap",
                    status: 0,
                    subNavigations: [],
                    url: "//service.taobao.com/support/leave_word_list.htm?nekot=1410939138028",
                  },
                ],
                url: "//refund.taobao.com/refund_list.htm?nekot=1410939138028",
              },
            ],
            url: "",
          },
        ],
        recentVisitStatus: 0,
      },
      status: 0,
      message: "nope",
    },
    p = {
      _description: "Mytaobao Base Module",
      _searchType: "item",
      selectSideMenuItem: function (a) {
        var b, c;
        (b = g.get("#" + a)),
          b &&
            ("A" !== b.nodeName.toUpperCase() && (b = g.get("A", b)),
            g.addClass(b, "selected"),
            (c = g.parent(b, ".J_MtSideTree")),
            c && g.replaceClass(c, "fold", "unfold"));
      },
      init: function () {
        var b = this;
        (window.selectItem = b.selectSideMenuItem),
          a.available("#J_MtNotice", function () {
            b._initNotice();
          }),
          a.available("#J_MtSideMenu", function () {
            b._initAvatar();
          }),
          a.ready(function () {
            g.query("LI", g.get("#J_MtMainNav"));
            b._initNavMenu(),
              b._initSearch(),
              b._initMenu(),
              b._initHandheldSubNav();
          });
      },
      _initHandheldSubNav: function () {
        if (a.all && a.one("#J_Nav_Side")) {
          g.get("#J_MtSideMenu") ||
            (a.one("#J_Nav_Side").remove(),
            a.one(".mt-logo").css("margin-left", "0px"));
          var c = b.mobile ? "tap swipe" : "click",
            d = a.all,
            e = {
              targetNode: d("#J_Nav_Side"),
              mainNav: d("#J_Col_Main"),
              subNav: d("#J_Col_Sub"),
              hide: function () {
                this.mainNav.removeClass("mainMarginLeft"),
                  this.targetNode.removeClass("show");
              },
              show: function () {
                this.mainNav.addClass("mainMarginLeft"),
                  this.targetNode.addClass("show");
              },
              renderEvent: function () {
                var e = this,
                  f = a.one("#J_Col_Sub");
                e.targetNode.on(c, function (a) {
                  a.halt(),
                    a.preventDefault(),
                    d(this).hasClass("show") ? e.hide() : e.show(),
                    "undefined" != typeof MT && MT.tracelog("sns.20.14");
                }),
                  b.mobile ||
                    d(document.body).on("click", function (a) {
                      (!f || (!f.contains(a.target) && f[0] != a.target)) &&
                        e.hide();
                    });
              },
            },
            f = {
              bindEvent: function () {
                d(document.body).on("swipe", function (a) {
                  var b = d(a.target);
                  return b.parent(".scrollable-panel")
                    ? void a.preventDefault()
                    : ("right" == a.direction && (a.preventDefault(), e.show()),
                      void (
                        "left" == a.direction && (a.preventDefault(), e.hide())
                      ));
                }),
                  d(document.body).on("tap", function (a) {
                    var b = (a.touch, d(a.target));
                    d("#J_Col_Sub") &&
                      !d("#J_Col_Sub").contains(b) &&
                      "J_Col_Sub" != b[0].id &&
                      e.hide();
                  });
              },
            };
          e.renderEvent(), b.mobile && f.bindEvent();
        }
      },
      _initNavMenu: function () {
        function d() {
          m && m.cancel && m.cancel();
        }
        function e() {
          q && q.cancel && q.cancel();
        }
        function f() {
          s = "show";
          var b = c();
          if (b) {
            var d = a.all(l);
            d.removeClass(n),
              d.css({ opacity: 0, "margin-top": "-15px" }),
              d
                .stop()
                .animate(
                  { opacity: 1, "margin-top": "0" },
                  { duration: 0.2, easing: "easeInStrong" }
                );
          } else g.removeClass(l, n);
        }
        function i() {
          s = "hide";
          var b = c();
          if (b) {
            var d = a.all(l);
            d.stop().animate(
              { opacity: 0, "margin-top": "-15px" },
              {
                duration: 0.2,
                easing: "easeInStrong",
                complete: function () {
                  d.addClass(n);
                },
              }
            );
          } else d.hide(), g.addClass(l, n);
        }
        if (!b.mobile) {
          var j = g.get("#J_MtMainNav"),
            k = g.query(".J_MtNavSubTrigger .mt-nav-parent", j),
            l = g.query(".J_MtNavSub", j),
            m = null,
            n = "hide",
            o = "mt-nav-sub-wrap",
            p = 200,
            q = null,
            r = 200,
            s = (b.mobile ? "tap" : "mouseenter", "hide");
          h.on(k, "mouseenter", function (b) {
            g.children(b.currentTarget, ".J_MtNavSub");
            d(),
              "hide" === s &&
                (q = a.later(function () {
                  g.addClass(b.currentTarget, o), f();
                }, r));
          }),
            h.on(k, "mouseleave", function (b) {
              g.children(b.currentTarget, ".J_MtNavSub");
              e(),
                (m = a.later(function () {
                  i(), g.removeClass(b.currentTarget, o);
                }, p));
            }),
            h.on(l, "mouseenter", d),
            h.on(l, "mouseleave", function (b) {
              var c = g.parent(b.target, "LI");
              m = a.later(function () {
                i(), g.removeClass(c, o);
              }, p);
            });
        }
      },
      _initNotice: function () {
        g.get("#system-announce") ||
          (g.show("#J_MtNotice"), g.addClass("body", "mt-notice-on"));
      },
      _initAvatar: function () {
        var a = g.get("#J_MtAvatarBox"),
          b = (g.get("#J_MtAvatar"), g.get("#J_MtAvatarOperation"));
        a &&
          (h.on(a, "mouseenter", function (a) {
            g.removeClass(b, "hide");
          }),
          h.on(a, "mouseleave", function (a) {
            g.addClass(b, "hide");
          }));
      },
      _initSearch: function () {
        var b = ",tbc/search-suggest/1.3.9/",
          c = ["dom", "index", "new_suggest.css"],
          d = (TB.Global.isLogin, ["list"]);
        a.use(c.join(b), function (a, b, c) {
          new c({
            plugins: [],
            sugConfig: {
              sourceUrl: "//suggest.taobao.com/sug?k=1",
              node: "#q",
              focused: !1,
              resultFormat: "",
            },
            mods: { sort: d },
          });
        });
      },
      initSearchType: function (b) {
        var c = this,
          d = g.query(b, g.get("#J_MtSearch"))[0];
        d &&
          (h.on(d, "mouseenter mouseleave", function (a) {
            "mouseenter" == a.type
              ? g.addClass(this, "hover")
              : g.removeClass(this, "hover");
          }),
          h.on(g.query("dt", d), "click", function (b) {
            var e = a.get("a", this),
              f = g.attr(e, "data-type"),
              h = n._getSearchURL(f);
            g.attr(n._searchForm(), "action", h),
              (c._searchType = f),
              g.prepend(this, a.get("dl", d)),
              g.removeClass(d, "hover");
          }));
      },
      _loadQzData: function () {
        var b = "GROUPLUS_567_" + g.attr(g.get("#J_quanzi"), "data-userid"),
          c =
            location.host.indexOf(".daily.") > -1
              ? "count.config-vip.taobao.net:8888/counter3"
              : "count.taobao.com/counter5",
          d = {
            checkResult: !1,
            emptyDataNode: g.get("#J_EmptyData"),
            targetNode: g.get("#J_GetData"),
            _ajaxCheck: location.protocol + "//" + c + "?keys=" + b,
            _ajaxConURL: g.attr(g.get("#J_GetData"), "data-url-getcontent"),
            _ajaxCountURL: g.attr(
              g.get("#J_GetData"),
              "data-url-getupdatingcount"
            ),
            _XHR: function (b, c, d, e) {
              var f = this;
              new a.IO({
                url: b,
                data: c,
                carset: "gbk",
                dataType: "jsonp",
                jsonp: "callback",
                success: function (a) {
                  var b = a;
                  d && d.call(f, b);
                },
                error: function (a) {
                  f._errorExe();
                },
              });
            },
            _errorExe: function () {
              g.removeClass(this.emptyDataNode, "hide"),
                g.addClass(this.targetNode, "hide");
            },
            _requireConCallBack: function (a) {
              1 == a.code || "1" == a.code
                ? ((new Image().src =
                    "//log.mmstat.com/sns.17.23?cache=" + new Date().getTime()),
                  g.html(this.targetNode, a.html),
                  g.html(g.get("#J_QzNum"), a.groupnum))
                : this._errorExe();
            },
            _requireCountCallBack: function (a) {
              if (1 == a.code || "1" == a.code) {
                if ("0" == a.updateCount) return;
                g.html(g.get("#J_QzNum"), "(" + a.updateCount + ")");
              } else this._errorExe();
            },
            _requireCheck: function (c) {
              var d = this;
              new a.IO({
                url: d._ajaxCheck,
                carset: "gbk",
                dataType: "jsonp",
                jsonp: "callback",
                async: !1,
                success: function (a) {
                  return 0 == a[b]
                    ? void d._errorExe()
                    : ("CountData" == c ||
                        ("ContData" == c &&
                          d._XHR(d._ajaxConURL, null, d._requireConCallBack)),
                      void (d.checkResult = !0));
                },
                error: function (a) {
                  d._errorExe();
                },
              });
            },
            initCountData: function () {
              this._requireCheck("CountData");
            },
            getQzContData: function () {
              this._requireCheck("ContData");
            },
          };
        return d;
      },
      _initMenu: function () {
        function b(b) {
          if (e.enableFetchRemoteMenu) {
            var c = [],
              h = !1;
            c.push(
              '<div class="mt-menu-tree">',
              '<dl class="mt-menu-item" data-spm="a2109">'
            );
            var i = [];
            a.each(b.navigations, function (a) {
              i = i.concat(a.subNavigations);
            }),
              a.each(
                i.sort(function (a, b) {
                  return a.order - b.order;
                }),
                function (d) {
                  if (0 === d.status) {
                    if (503 === d.navigationId) return void (h = !0);
                    c.push(
                      l[d.navigationId] && 1 === b[l[d.navigationId]]
                        ? '<dd class="mt-menu-sub unfold J_MtSideTree">'
                        : '<dd class="mt-menu-sub unfold fold J_MtSideTree">',
                      '<a href="',
                      d.url,
                      '"',
                      "#" === d.url ? ' class="J_MtIndicator" ' : "",
                      'data-spm="',
                      d.spm,
                      '">',
                      d.name,
                      "</a>"
                    ),
                      d.subNavigations &&
                        d.subNavigations.length &&
                        (c.push(
                          '<b class="mt-indicator J_MtIndicator" data-navigationId="',
                          d.navigationId,
                          '" >-</b>',
                          '<ul class="mt-menu-sub-content">'
                        ),
                        a.each(
                          d.subNavigations.sort(function (a, b) {
                            return a.order - b.order;
                          }),
                          function (a) {
                            0 === a.status &&
                              c.push(
                                "<li >",
                                '<a href="',
                                a.url,
                                '" data-spm="',
                                a.spm,
                                '">',
                                a.name,
                                "</a>",
                                "</li>"
                              );
                          }
                        ),
                        c.push("</ul>")),
                      c.push("</dd>");
                  }
                }
              ),
              h &&
                c.push(
                  '</dl><p class="hide J_RecentVisitPlaceholder" ></p></div>'
                ),
              g.replaceWith(
                g.get("#J_MtSideMenu .mt-menu-tree"),
                g.create(c.join(""))
              );
          }
          d(), f();
        }
        function d() {
          function b(a) {
            var b = a.clone(!0),
              c = 145;
            return (c = a.data(i))
              ? c
              : (b.css({
                  position: "absolute",
                  left: "-999px",
                  top: "-999px",
                  visibility: "hidden",
                  display: "block",
                  height: "auto",
                }),
                a.after(b),
                (c = b.height()),
                b.remove(),
                a.data(i, c),
                c);
          }
          var d = g.query(".J_MtIndicator"),
            e = "fold",
            f = "un" + e,
            i = "calced_height",
            k = g.attr(d, "data-navigationId");
          d &&
            h.on(d, "click", function (d) {
              d.preventDefault();
              var h,
                i = d.target,
                l = g.parent(i, "DD"),
                m = c();
              m &&
                ((h = a.all(l).all(".mt-menu-sub-content")),
                h.css("overflow", "hidden")),
                g.hasClass(l, e)
                  ? (j.changeFoState(k, 2),
                    m && h.css("height", 0),
                    g.replaceClass(l, e, f),
                    m &&
                      h.stop().animate(
                        { height: b(h) },
                        {
                          duration: 0.3,
                          easing: "easeInStrong",
                          complete: function () {
                            h.css("height", "auto");
                          },
                        }
                      ))
                  : (j.changeFoState(k, 1),
                    m
                      ? h.stop().animate(
                          { height: 0 },
                          {
                            duration: 0.3,
                            easing: "easeInStrong",
                            complete: function () {
                              g.replaceClass(l, f, e), h.css("height", "auto");
                            },
                          }
                        )
                      : g.replaceClass(l, f, e));
            });
        }
        function f() {
          var b;
          b =
            location.host.indexOf(".daily.") > -1
              ? "//i.daily.taobao.net/my_taobao_api/recent_visit.json"
              : "//i.taobao.com/my_taobao_api/recent_visit.json";
          var d = g.get(".J_RecentVisitPlaceholder");
          d &&
            new a.IO({
              url: b,
              scriptCharset: "utf-8",
              dataType: "jsonp",
              success: function (b) {
                var e = b.data,
                  f = c();
                if (d && e && e.length) {
                  var h = [
                    '<dl data-spm="1998049103" class="mt-menu-item hide">',
                  ];
                  h.push("<dt>\u6700\u8fd1\u8bbf\u95ee</dt>");
                  for (var i = 0, j = e.length; j > i; i++) {
                    var k = e[i];
                    h.push(
                      '<dd><a data-spm="' + k.spm + '" href="',
                      a.escapeHtml(k.url),
                      '" target="_blank" role="menuitem" >',
                      a.escapeHtml(k.bizName),
                      "</a></dd>"
                    );
                  }
                  h.push("</dl>");
                  var l = g.create(h.join(""));
                  if ((g.replaceWith(d, l), f)) {
                    var m = a.all(l);
                    m.hide().fadeIn(0.5), g.removeClass(l, "hide");
                  } else g.removeClass(l, "hide");
                }
              },
            });
        }
        if (g.get("#J_EMS")) return d(), void f();
        j.on("refresh", function () {
          var a = j.getData();
          if (a) {
            try {
              console.log("refresh data", a);
            } catch (c) {}
            b(a);
          }
        }),
          j.on("saveDone", function () {
            j.fetchData();
          }),
          j.fetchData();
      },
    };
  p.init();
});
