$(document).ready(function(){  
  $("#loginimg").click(function(){  
  	$("#login").css('display','none');
  	$("#erm").css('display','block');
  });  
  
   $("#ermimg").click(function(){  
  	$("#login").css('display','block');
  	$("#erm").css('display','none');
  }); 
})