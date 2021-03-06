var removeRePin;

removeRePin = function(e, y) {
  var result;
  result = window.confirm("Are you sure you want to remove this picture ?");
  if (result) {
    return $.get("/remove-from-own-getlist", {
      pinid: e,
      repinid: y
    }, function(response) {
      var id;
      if (response.error) {
        alert("An error occured, please refresh the page and try again later");
      } else {
        id = "#horz-pin" + e;
        $(id).slideToggle();
      }
    });
  }
};

(function() {
  var dragging_header_background, otherX, otherY, x, y;
  $("#save_thumbnail_edit").click(function() {
    location.reload(true);
  });
  $("#set_as_profile_pic").click(function() {
    var picid;
    picid = $(".modal .active img").attr("picid");
    return $.get("/setprofilepic/" + picid, function(response) {
      location.reload(true);
    });
  });
  dragging_header_background = false;
  x = 0;
  y = 0;
  otherX = 0;
  otherY = 0;
  $("#header_background").mousedown(function(e) {
    var _ref;
    _ref = void 0;
    x = e.pageX;
    y = e.pageY;
    _ref = $(this).css("background-position").split(" ");
    otherX = _ref[0];
    otherY = _ref[1];
    return dragging_header_background = true;
  });
  $("body").mouseup(function() {
    var tempX, tempY, _ref;
    tempX = void 0;
    tempY = void 0;
    _ref = void 0;
    if (dragging_header_background) {
      dragging_header_background = false;
      _ref = $("#header_background").css("background-position").split(" ");
      otherX = _ref[0];
      otherY = _ref[1];
      tempX = parseInt(otherX.slice(0, +(otherX.length - 2) + 1 || 9e9));
      tempY = parseInt(otherY.slice(0, +(otherY.length - 2) + 1 || 9e9));
      return $.post("/changebgpos", {
        x: tempX,
        y: tempY
      });
    }
  });
  $("#header_background").mousemove(function(e) {
    var tempY, upload;
    tempY = void 0;
    if (dragging_header_background) {
      upload = false;
      tempY = parseInt(otherY.slice(0, +(otherY.length - 2) + 1 || 9e9));
      if (tempY + (e.pageY - y) < 0) {
        return $(this).css("background-position", otherX + " " + (tempY + (e.pageY - y)) + "px");
      }
    }
  });
  $("#switch5_wrapper").mouseover(function() {
    return $("#menu5").show();
  });
  $("#switch5_wrapper").mouseout(function() {
    return $("#menu5").hide();
  });
  return $("#myTab a").click(function(e) {
    e.preventDefault();
    $(this).tab("show");
  });
}).call(this);
