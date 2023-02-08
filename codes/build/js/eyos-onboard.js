AWS.config.update({
                region: 'ap-southeast-1',
                credentials: new AWS.CognitoIdentityCredentials({
                    IdentityPoolId: 'ap-southeast-1:cf979d4a-cf88-4155-b0d6-587e77aedba4'
                })
            });

var s3 = new AWS.S3({
                params: {Bucket: 'install.emporio.ai'},
        });
		
//lang stuff
function hideLang() {
$('[lang*="id"]').hide();
$('[lang*="th"]').hide();
$('[lang*="en"]').hide();
};

hideLang();
$('[lang*="en"]').show();

function langChange(event) {
	countrySet(event.value);
}


function getLocation() {
	console.log("getting loc");
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(showPosition);
  } else {
    console.log("Geolocation is not supported by this browser.");
  }
}

function showPosition(position) {
  console.log(position);
  lat = document.getElementById('storeLatitude');
  lon = document.getElementById('storeLongitude');
  lat.value = position.coords.latitude;
  lon.value = position.coords.longitude;
}

function copyStoreAddress() {
	const fields = ['Name','Address','City','PostCode']
	for (let i = 0; i < fields.length; i++) {
		field = fields[i];
		document.getElementById('retailer' + field).value = document.getElementById('store' + field).value;
		console.log(document.getElementById('store' + field).value);
	}
}

function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function s3upload(id) {
   //var files = document.getElementById('storeFrontPhoto').files;
   var files = document.getElementById(id).files;
   if (files) 
   {
	 var guid = uuidv4();  
     var file = files[0];
     var fileName = file.name;
	 var fileExt = file.name.split(".")[1]
     var filePath = 'store_photos/' + guid + '.' + fileExt;
     var fileUrl = 'https://ap-southeast-1.amazonaws.com/install.emporio.ai/' +  filePath;
	 console.log('filepath is');
	 console.log(filePath);
	 
	 document.getElementById(id + 's3').value = fileUrl;
	 console.log('value is');
	 console.log(document.getElementById(id + 's3').value);
     s3.upload({
        Key: filePath,
        Body: file
        }, function(err, data) {
        if(err) {
        console.log('error');
		console.log(err);
        }
        alert('Successfully Uploaded!');
        }).on('httpUploadProgress', function (progress) {
        var uploaded = parseInt((progress.loaded * 100) / progress.total);
        $("progress").attr('value', uploaded);
      });
   }
};

function formSubmit(event) {
  var url = "https://088u31uofi.execute-api.ap-southeast-1.amazonaws.com/default/connect_onboarding_form";
  var request = new XMLHttpRequest();
  request.open('POST', url, true);
  request.onload = function() { // request successful
  // we can use server response to our request now
    //console.log(request);
    console.log(request.responseText);
	//document.getElementById('response').innerHTML = request.responseText;
	document.getElementById('formOnboard').style = "display: none";
	var jsonResponse = JSON.parse(request.responseText);
	var contractURL = jsonResponse['contractURL'];
	var storeCode = jsonResponse['storeCode'];
	var storeName = jsonResponse['storeName'];
	document.getElementById('tncFrame').src = contractURL;
	document.getElementById('store_info').style = "";
	document.getElementById('store_data').innerHTML = storeName + " | " + storeCode;
	document.getElementById('tncFrame').style = "width: 80vw; height: 200vw;";
  };

  request.onerror = function() {
  };
  console.log(event.target);
  var formData = new FormData(event.target);
  formData.delete('storeFrontPhoto');
  formData.delete('storeShelfPhoto');
  formData.delete('storeTillPhoto');
  request.send(formData); // create FormData from form that triggered event
  event.preventDefault();
  return false;
}

var input = document.getElementById('ownerMobile');
  errorMsg = document.querySelector("#error-msg"),
  validMsg = document.querySelector("#valid-msg");

// here, the index maps to the error code returned from getValidationError - see readme
var errorMap = ["Invalid number", "Invalid country code", "Too short", "Too long", "Invalid number"];
var iti = window.intlTelInput(input, {
  utilsScript: "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.8/js/utils.js",
  initialCountry: "auto",
  geoIpLookup: function(success, failure) {
    $.get("https://ipinfo.io", function() {}, "jsonp").always(function(resp) {
      var countryCode = (resp && resp.country) ? resp.country : "us";
      success(countryCode);
	  countrySet(countryCode);
    });
  },
});

var reset = function() {
  input.classList.remove("error");
  errorMsg.innerHTML = "";
  errorMsg.classList.add("hide");
  validMsg.classList.add("hide");
};

// on blur: validate
input.addEventListener('blur', function() {
  reset();
  if (input.value.trim()) {
    if (iti.isValidNumber()) {
      validMsg.classList.remove("hide");
	  document.getElementById('ownerMobile').value = iti.getNumber(intlTelInputUtils.numberFormat.E164);
    } else {
      input.classList.add("error");
      var errorCode = iti.getValidationError();
      errorMsg.innerHTML = errorMap[errorCode];
      errorMsg.classList.remove("hide");
    }
  }
});

// on keyup / change flag: reset
input.addEventListener('change', reset);
input.addEventListener('keyup', reset);

function countrySet(country) {
	console.log('setting country' + country);
	console.log(country);
	if (country == 'ID' || country == 'TH') {
		hideLang();
	    $('[lang*="' + country + '"]').show();
		console.log(country);
		document.getElementById('Country').value=country;
		if (country == 'ID') {
					dropDownImport('data/cities_id.csv', 'storeCity')
		dropDownImport('data/cities_id.csv', 'retailerCity')
		dropDownImport('data/asm_kam_id.csv', 'storeASM')
		} else {
			dropDownImport('data/cities_th.csv', 'storeCity')
			dropDownImport('data/cities_th.csv', 'retailerCity')

		}
	} else {
		hideLang();
		$('[lang*=en]').show();
		dropDownImport('data/cities_id.csv', 'storeCity')
		dropDownImport('data/cities_id.csv', 'retailerCity')
		dropDownImport('data/asm_kam_id.csv', 'storeASM')
	}
};

function setTesting(item) {
	if ($('#' + item.id + '').is(":checked"))
		{
		  console.log('checked');
		  document.getElementById('isTest').value = 'true'
		} else {
			console.log('not checked');
			document.getElementById('isTest').value = 'false'
		}
		console.log(document.getElementById('isTest').value);
};

function setCity(country){
	console.log('setting city ' + country);
	if (country == 'TH'){
		url = "data/cities_th.csv"
	} else {
		var url = "data/cities_id.csv";
	}
	$(document).ready(function() {
		$.ajax({
			type: "GET",
			url: url,
			dataType: "text",
			success: function(data) {processData(data);}
		 });
	});

	function processData(allText) {
		try {
			$('#storeCity').selectize()[0].selectize.destroy();
			$('#retailerCity').selectize()[0].selectize.destroy();
		} catch(err) {
			console.log(err)
		}
		var allTextLines = allText.split(/\r\n|\n/);
		console.log(allTextLines);
		var headers = allTextLines[0].split(',');
		var selectStore = document.getElementById("storeCity");
		var selectRetailer = document.getElementById("retailerCity");
		//disable existing selectize
		
		removeOptions(selectStore);
		removeOptions(selectRetailer);
		var defaultOption = document.createElement("option");
		defaultOption.text = "Please Choose...";
		defaultOption.value = "";
		defaultOption.disabled = true;
		defaultOption.hidden = true;
		defaultOption.selected = true;
		selectStore.appendChild(defaultOption);
		selectRetailer.appendChild(defaultOption.cloneNode(true));

		for (var i=1; i<allTextLines.length; i++) {
			var data = allTextLines[i].split(',');
			if (data.length == headers.length) {
				for (var j=0; j<headers.length; j++) {
					var option = document.createElement("option");
					option.text = data[j];
					option.value = data[j];
					selectStore.appendChild(option);
					selectRetailer.appendChild(option.cloneNode(true));
				}
			}
		}
		//change to text & select
		console.log(selectStore);
storeCitySelect = $("#storeCity").selectize({
  create: false,
  placeholder: 'Please Choose...',
})[0].selectize;
storeCitySelect.refreshOptions();
storeRetailerSelect = $("#retailerCity").selectize({
  create: false,
    placeholder: 'Please Choose...'
})[0].selectize;
		//alert(lines);
	}
}

function dropDownImport(file, id){
	console.log('setting ' + file + ' to ' + id);
	
	$(document).ready(function() {
		$.ajax({
			type: "GET",
			url: file,
			dataType: "text",
			success: function(data) {processData(data);}
		 });
	});

	function processData(allText) {
		try {
			$('#' + id + '').selectize()[0].selectize.destroy();
		} catch(err) {
			console.log(err)
		}
		var allTextLines = allText.split(/\r\n|\n/);
		console.log(allTextLines);
		var headers = allTextLines[0].split(',');
		var selector = document.getElementById(id);
		//disable existing selectize
		
		removeOptions(selector);
		var defaultOption = document.createElement("option");
		defaultOption.text = "Please Choose...";
		defaultOption.value = "";
		defaultOption.disabled = true;
		defaultOption.hidden = true;
		defaultOption.selected = true;
		selector.appendChild(defaultOption);

		for (var i=1; i<allTextLines.length; i++) {
			var data = allTextLines[i].split(',');
			if (data.length == headers.length) {
				for (var j=0; j<headers.length; j++) {
					var option = document.createElement("option");
					option.text = data[j];
					option.value = data[j];
					selector.appendChild(option);
				}
			}
		}
		//change to text & select
		console.log(selector);
selectorSelect = $('#' + id + '').selectize({
  create: false,
  placeholder: 'Please Choose...',
})[0].selectize;
selectorSelect.refreshOptions();
		//alert(lines);
	}
}

function removeOptions(selectElement) {
   var i, L = selectElement.options.length - 1;
   for(i = L; i >= 0; i--) {
      selectElement.remove(i);
   }
}
