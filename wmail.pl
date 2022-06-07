#!/usr/bin/perl

use strict;
use CGI;
# use CGI::Carp qw(fatalsToBrowser);

my %cf;

# my $iam = $ENV{LOGNAME};
my $iam = `id -un`;
chomp($iam);

my $logfile = "/home/$iam/email.log";

main:
{
    %cf = read_config();

    my $query = new CGI();
    my %ch;
    #my %ch = $query->Vars();

    # https://metacpan.org/pod/CGI#CGI.pm-HAS-BEEN-REMOVED-FROM-THE-PERL-CORE
    # https://metacpan.org/pod/CGI::Alternatives
    $ch{email1} = sanitize(scalar $query->param('email1'));
    $ch{email2} = sanitize(scalar $query->param('email2'));
    $ch{subject} = sanitize(scalar $query->param('subject'));
    $ch{message} = scalar $query->param('message');

    # Passing the message through CGI a second time trims off
    # trailing whitespace. We need to take care of that on the first pass
    # so that the md5sub will work.

    $ch{message} =~ s/\s+\Z//s;

    $ch{send} = $query->param('send');
    $ch{confirm} = $query->param('confirm');
    
    if ($ch{send})
    {
	if (! $ch{email1})
	{
	    $ch{warning} .= "Missing email. You must enter your email address so we can reply to you.<br>\n";
	}
	elsif ($ch{email1} ne $ch{email2})
	{
	    $ch{warning} .= "Email addresses don't match.<br>\n";
	}
    }

    if ($ch{send} eq "Send")
    {
	my $test_c = confirm(\%ch);
	if ($test_c eq $ch{confirm})
	{
	    check_and_send(\%ch);
	}
	else
	{
	    $ch{warning} = "Please check your message.<br>\n";
	    $ch{send} = "Edit";
	}
    }

    my $all;
    if (! $ch{warning} && $ch{send})
    {
	if ($ch{send} eq "Preview")
	{
	    $ch{confirm} = confirm(\%ch);
	    $all = read_file("wmail_2.html");
	}
	elsif ($ch{send} eq "Edit")
	{
	    $all = read_file("wmail_1.html");
	}
	elsif ($ch{send} eq "Send")
	{
	    $all = read_file("wmail_thanks.html");
	}
    }
    else
    {
	$all = read_file("wmail_1.html");
    }
    $all =~ s/(?<!\\)(\$([\w\d]+))(?!=\w)(?!=\d)(?!=\z)/$ch{$2}/g;
    $all =~ s/\\([0-9]{3})/chr(oct($1))/eg;


    print "Content-Type: text/html; charset=iso-8859-1\n\n$all";
}

sub confirm
{
    my $cr = $_[0];
    my $confirm;
    
    # $confirm = `echo "$cf{random_string} $cr->{message}" | /usr/bin/sha1sum`;
    $confirm = `echo "$cf{random_string} $cr->{message}" | /usr/bin/md5sum`;
    $confirm =~ s/\s+(.*)//s;

    return $confirm;
}


sub check_and_send
{
    my $cr = $_[0];

    my $full_msg = sprintf("To: $cf{mail_to}\n");

    # Extra headers for tracking These two extra headers work fine with Gmail. Might break other email in the
    # future.
    $full_msg .= "X-remote-addr: $ENV{REMOTE_ADDR}\n";
    $full_msg .= "X-user-agent: $ENV{HTTP_USER_AGENT}\n";

    $full_msg .= sprintf("From: $cf{from}\n");
    $full_msg .= sprintf("Reply-To: $cr->{email1}\n");
    $full_msg .= sprintf("Subject: $cf{subject_prefix} $cr->{subject}\n\n");
    $full_msg .= sprintf("$cr->{message}\n");

    # Make /home/mst3k/email.log rw---rw- so that user nobody in group www can write it, but not anyone in
    # group users. This is a known thing for shared hosting, and relies on how linux group permissions work.
    
    if (open(MLOG, ">>", $logfile))
    {
# 	print MLOG "email1:$cr->{email1}\n";
# 	print MLOG "email2:$cr->{email2}\n";
# 	print MLOG "subject:$cr->{subject}\n";
# 	print MLOG "message:$cr->{message}\n";
# 	print MLOG "eof\n";
	print MLOG $full_msg;
	close(MLOG);
    }
    else
    {
	die "Can't open log: $logfile\n";
    }


    # Gmail needs cap R cap T Reply-To? (No.) Older mail systems may send this, but gmail (apps) won't reply
    # to the reply-to.

    if (open(MAIL, "|-", "/usr/sbin/sendmail -t"))
    {
	print MAIL $full_msg;
	close(MAIL);
    }
    elsif (open(LOG, ">>", $logfile))
    {
	print LOG "can't open sendmail\n";
	close(LOG);
    }
}

sub sanitize
{
    my $str = $_[0];
    $str =~ s/\;//g; # We're superstitious about ;
    $str =~ s/[\000-\037]//sg; # Remove control chars

    if (length($str) > 50)
    {
	$str = substr($str,0,50);
    }
    return $str;
}

sub read_file
{
    my @stat_array = stat($_[0]);
    if ($#stat_array < 7)
      {
        die "File $_[0] not found\n";
      }
    my $temp;

    #
    # It is possible that someone will ask us to open a file with a leading space.
    # That requires separate args for the < and for the file name. I did a test to confirm
    # this solution. It also works for files with trailing space.
    # 
    open(IN, "<", "$_[0]");
    sysread(IN, $temp, $stat_array[7]);
    close(IN);
    return $temp;
}

sub read_config
{
    my %cf = read_config_core();
    if (exists($cf{config_file}))
    {
	%cf = read_config_core($cf{config_file});
	return %cf;
    }
    else
    {
	die "Cannot load configuration.\n";
    }
}

sub read_config_core
{
    my %cf;
    my $all;
    if ($_[0])
    {
	$all = read_file($_[0]);
    }
    else
    {
	$all = read_file(".config");
    }

    #
    # These regex's are nice, but require \n line endings.
    # Missing = on a line silently fails to parse.
    #

    $all =~ s/\#(.*)//g; 	# remove comments to end of line
    $all =~ s/\s*=\s*/=/g;	# remove whitespace around = 
    $all =~ s/\s+\n/\n/g;	# remove trailing whitespace
    $all =~ s/\n\s+/\n/g;	# remove leading whitespace

    while($all =~ m/(.*)=(.*)/g)
    {
	$cf{$1} = $2;
    }

    # This is applicable to CGI scripts that have
    # .htaccess authentication
    
    $cf{login} = $ENV{REMOTE_USER};

    return %cf;
}
