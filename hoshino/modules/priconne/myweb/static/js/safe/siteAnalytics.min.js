function _loadAsyncJs(e) {
	var f = e;
	var d = document.getElementsByTagName("script");
	for (var a = 0; a < d.length; a++) {
		if (d[a].src == f) {
			return
		}
	}
	var b = document.createElement("script");
	b.type = "text/javascript";
	b.async = true;
	b.src = f;
	var c = d[0];
	c.parentNode.insertBefore(b, c)
}

function _getJsFilePath(b) {
	var a = document.location.hostname;
	var c = /^\w*?.suning.com$/;
	var f = /^\w*?pre.cnsuning.com$/;
	var e = /^\w*?sit.cnsuning.com$/;
	var d = "";
	if (c.test(a)) {
		d = ("https:" == document.location.protocol) ? "https://imgssl.suning.com" : "http://script.suning.cn"
	} else {
		if (f.test(a)) {
			d = ("https:" == document.location.protocol) ? "https://preimgssl.suning.com" : "http://prescript.suning.cn"
		} else {
			if (e.test(a)) {
				d = ("https:" == document.location.protocol) ? "https://sit1imgssl.suning.com" : "http://sit1script.suning.cn"
			} else {
				d = ("https:" == document.location.protocol) ? "https://preimgssl.suning.com" : "http://prescript.suning.cn"
			}
		}
	}
	d = d + "/javascript/sn_da/" + b;
	return d
}

function runAnalyseExpo() {
	if (typeof _analyseExpoTags == "function") {
		_analyseExpoTags("a")
	} else {
		setTimeout(runAnalyseExpo, 1000)
	}
};