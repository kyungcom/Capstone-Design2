    $(document).ready(function(){
        if("{{ session['id'] }}" == ""){
            alert("올바른 경로가 아닙니다.");
            location.href = "/";
        }
        console.log("이거 되냐?");
    });