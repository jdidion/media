#!/usr/bin/env perl

###############################################################################
# id3batch
#
# Batch retag files that use ID3 metadata. Tagging is based on file name. You
# supply a regexp with one or more capture groups, and the frames to which
# those groups correspond (comma-delimited).
#
# For example:
#   Files named like: 1. Joe Blow - Blowin Up Da Spot - B to the Lizzo!.mp3
#   You want to make the song title "1. B to the Lizzo!"
#   id3batch ~/music "(\d+\.) Joe Blow - Blowin Up Da Spot - (.+?)\.mp3" song,1,2
#
# This says that you want to take the first two capture groups, join them (using
# space by default, unless you specify the "-s" option) and set the SONG frame of
# the ID3 metadata to the result. Specifying the directory containing the files
# is optional - current directory is used by default. You can make it recursive
# with the "-r" option.
###############################################################################

use strict;
use warnings;
use autodie qw(system);

use File::Basename;
use File::Spec::Functions;
use Getopt::Long qw(:config no_ignore_case auto_help);

my %opt = (
    id3_command => 'id3v2',
    quiet       => 0,
    recursive   => 0,
    separator   => ' ',
    test        => 0,
);

GetOptions(\%opt,
    'convert|c',
    'fix_genre|g',
    'quiet|q',
    'recursive|r',
    'separator|s=s',
    'id3_command=s',
    'test|t',
) or die 'Invalid options';

my $in = shift;
my $re;
my %frames;

if (scalar(@ARGV)) {
    my $pattern = shift;
    $re = qr/$pattern/;
    foreach (@ARGV) {
        my @f = split(',', $_);
        my $name = shift(@f);
        $frames{$name} = [ map {int($_)-1} @f ];
    }
}

sub retag {
    my $in = shift;
    my @files;
    if (-f $in) {
        push(@files, $in);
    }
    elsif (-d $in) {
        opendir(my $DIR, $in);
        for my $f (readdir($DIR)) {
            next if ($f =~ /^\./);
            push(@files, catfile($in, $f));
        }
        closedir($DIR);
    }
    for my $file (@files) {
        if (-f $file) {
            if ($opt{convert}) {
                eval {
                    system("$opt{id3_command} -C \"$file\"") unless $opt{test};
                    1;
                } or do {
                    print "Convert failed: $@\n";
                }
            }
            
            if ($opt{fix_genre}) {
                unless ($opt{test}) {
                    my $genre_str = qx($opt{id3_command} -q TCON \"$file\");
                    my $genre = ($genre_str =~ /[^\w]*(.+?) /)[0];
                    if ($genre) {
                        system("$opt{id3_command} -g $genre \"$file\"") unless $opt{test};
                    }
                }
            }
            
            if (defined($re)) {
                my @groups = basename($file, '.mp3') =~ $re or next;
                my $opts;
                for my $name (keys(%frames)) {
                    my @group_idx = @{$frames{$name}};
                    my $value = join($opt{separator}, @groups[@group_idx]);
                    $opts .= " --${name} \"${value}\"";
                }
            
                my $cmd = "$opt{id3_command}${opts} \"$file\"";
                print "$cmd\n" unless $opt{quiet};
                eval {
                    system $cmd unless $opt{test};
                    1;
                } or do {
                    print "Command failed: $@\n";
                }
            }
        }
        elsif (-d $file && $opt{recursive}) {
            retag($file);
        }
    }
}

retag($in);