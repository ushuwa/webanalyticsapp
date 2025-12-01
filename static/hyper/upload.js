
function initUploads() {

    Dropzone.autoDiscover = false;

    new Dropzone("#myAwesomeDropzone", {
        url: "/upload",                
        maxFilesize: 10,               
        acceptedFiles: ".csv",         
        uploadMultiple: false,
        addRemoveLinks: false,
        previewsContainer: "#file-previews",
        previewTemplate: document.querySelector("#uploadPreviewTemplate").innerHTML,
        dictInvalidFileType: "Only CSV files are allowed."  
    });
}
