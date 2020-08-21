function validText(txt) {
    var bt = document.getElementById('submit');
    var ele = document.getElementsByTagName('input');            

    // Loop through each element.
    for (i = 0; i < ele.length; i++) {

        // Check that all input values are filled
        if (ele[i].value == '') {
            bt.disabled = true;    // Disable the button.
            return false;
        }
        else {
            bt.disabled = false;   // Enable the button.
        }
    }
}

function validNum(num) {
    var bt = document.getElementById('submit');
    var ele = document.getElementById('num').value;

    if (ele > 0) {
        bt.disabled = false;
        return true;
    }
    
}