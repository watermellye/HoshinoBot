window.onload = function () {
    //获取需要悬浮的对象
    let user = document.getElementById("user");
    //获取被隐藏的菜单
    let menu = document.getElementById("menu");

    ////给user添加鼠标悬浮事件
    //user.onmouseover = function () {
    //    //改变菜单的内联样式display为block
    //    menu.style.display = "block";
    //}

    //
    user.onmouseout = function () {
        //获取菜单栏的坐标值
        let menux = menu.offsetLeft;
        let menuy = menu.offsetTop;
        let menuX = menu.offsetLeft + menu.offsetWidth;
        let menuY = menu.offsetTop + menu.offsetHeight;

        //获取鼠标的坐标值
        let event = window.event;
        let mouseX = event.clientX;
        let mouseY = event.clientY;

        if (mouseX < menux || mouseX > menuX || mouseY < menuY || mouseY > menuY) {
            menu.style.display = "none";
        }
    }

    //分别给menu对象绑定鼠标悬浮和鼠标离开事件
    menu.onmouseover = function () {
        menu.style.display = "block";
    }
    menu.onmouseleave = function () {
        menu.style.display = "none";
    }
}
