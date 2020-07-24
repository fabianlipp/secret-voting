$(document).ready(function() {
    // Use a "/test" namespace.
    // An application can open a connection on multiple namespaces, and
    // Socket.IO will multiplex all those connections on a single
    // physical channel. If you don't care about multiple channels, you
    // can set the namespace to an empty string.
    namespace = '/test';

    // Connect to the Socket.IO server.
    // The connection URL has the following format, relative to the current page:
    //     http[s]://<domain>:<port>[/<namespace>]
    var socket = io(namespace, {query: "token=" + secret_voting_token});

    // Event handler for new connections.
    // The callback function is invoked when a connection with the
    // server is established.
    //socket.on('connect', function() {
    //    socket.emit('my_event', {data: 'I\'m connected!'});
    //});

    socket.on('register_broadcast', function(msg) {
        updateListOfUsers(msg.registered_fullnames)
    });

    socket.on('register_response', function(msg) {
        if (msg.successful) {
            $('#register_success').html("You registered successfully. <b>Do not close the window!</b>");
            setControlState(true);
        } else {
            $('#register_success').html("Could not register.");
        }
    });

    socket.on('reset_broadcast', function(msg) {
        $("#list_of_users").html('');
        $("#register_success").html('');
        $("#your_token").val('');
        $('#voting_title').html(msg.voting_title);
        $("#admin_output_tokens").html('');
        $("#admin_output_names").html('');
        setState(true);
        setControlState(false);
    });

    socket.on('voting_end_broadcast', function(msg) {
        setControlState(true);
        setState(false);
    });

    socket.on('generated_token', function (msg) {
        var yourToken = $('#your_token');
	    yourToken.val(msg.token);

        var votingLink = $('#voting_link');
        votingLink.html('Copy token and open ballot box: <a href="'+msg.voting_link+'" target="_blank">'+msg.voting_link+'</a>');
	
	    var copyBtn = $('#copy_btn');
	    copyBtn.click(function () {
            yourToken.select();
            if (typeof yourToken.setSelectionRange === "function") yourToken.setSelectionRange(0,9999);
            document.execCommand('copy');
	    });
        copyBtn.prop("disabled", false);

        $('#register_btn').prop("disabled", true);
    });

    socket.on('initial_status', function (msg) {
        updateListOfUsers(msg.registered_fullnames);

        setState(msg.registration_active);
        if (msg.registration_active && !msg.already_registered) {
            setControlState(false);
        } else {
            setControlState(true);
        }
        $('#voting_title').html(msg.voting_title);
        $("#fullname").val(msg.fullname);
        $("#connection_state").html("Connected");
        if (msg.admin_state) {
            $("#admin_state").html("true");
        } else {
            $("#admin_state").html("false");
        }
    });

    socket.on('disconnect', function (msg) {
        $("#connection_state").html("Not Connected");
    });

    socket.on('voting_end_response', function (msg) {
        let list_contents = ""
        for (name of msg.all_users) {
            list_contents += '<li>' + name + '</li>\n';
        }
        $("#admin_output_names").html(list_contents);
        list_contents = ""
        for (name of msg.all_tokens) {
            list_contents += '<li>' + name + '</li>\n';
        }
        $("#admin_output_tokens").html(list_contents);
        json_output = {
            "users": msg.all_users,
            "tokens": msg.all_tokens
        };
        let allTokens = $("#admin_output_json");
        allTokens.val(JSON.stringify(json_output));
	    
        let copyBtn = $('#copy_btn');
	    copyBtn.click(function () {
            allTokens.select();
            if (typeof allTokens.setSelectionRange === "function") allTokens.setSelectionRange(0,9999);
            document.execCommand('copy');
	    });
        copyBtn.prop("disabled", false);
    });

    // Handlers for the different forms in the page.
    // These accept data from the user and send it to the server in a
    // variety of ways

    // User controls
    $('form#voting_register').submit(function(event) {
        socket.emit('voting_register', {});
        return false;
    });

    // Admin controls
    $('form#voting_start').submit(function(event) {
        socket.emit('admin_voting_start', {
            'voting_title': $("input#voting_title").val(),
            'voting_link': $("input#voting_link").val()
        });
        return false;
    });
    $('form#voting_end').submit(function(event) {
        socket.emit('admin_voting_end', {});
        return false;
    });
});

function setState(registrationActive) {
    if (registrationActive) {
        $('#state').html("Registration is active")
    } else {
        $('#state').html("Registration is inactive")
    }
}

function setControlState(registrationDisabled) {
    $("#voting_register :input").prop('disabled', registrationDisabled);
    $("#voting_start :input").prop('disabled', !registrationDisabled);
    $("#voting_end :input").prop('disabled', registrationDisabled);
}

function updateListOfUsers(all_users) {
    let list_contents = ""
    for (name of all_users) {
        list_contents += '<li>' + name + '</li>\n';
    }
    $("#list_of_users").html(list_contents);
    $("#num_of_users").html(all_users.length);
}
