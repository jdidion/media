require 'erb'
require 'amazon/ecs'
require 'config.rb'
include Amazon

def read_file(path, name = nil)
  if name
    path = File.join(path, name)
  end
  s = ""
  File.open(path, "r") do |file|
    s = file.read
  end
  return s
end


# returns status,content
# status: :ok, :timeout, :error
def read_url(url, sec = nil, prefix = nil, limit = 10)
  status = :ok
  content = nil

  begin
    if sec
      begin
        Timeout::timeout(sec) do
          content = fetch(url, prefix, limit)
        end
      rescue Timeout::Error
        status = :timeout
        content = nil
      end
    else
      content = fetch(url, prefix, limit)
    end
  rescue Exception => e
    status = :error
    content = e
  end

  return status,content
end

def fetch(uri_str, prefix, limit = 10)
  raise ArgumentError, 'HTTP redirect too deep' if limit == 0

  response = Net::HTTP.get_response(URI.parse(uri_str))
  case response
  when Net::HTTPSuccess
    response.body
  when Net::HTTPRedirection
    redir = response['location']
    if !(redir =~ /^http\/\/.*$/) && !prefix.nil?
      redir = URI.join(prefix, redir).to_s
    end
    fetch(redir, limit - 1)
  else
    response.error!
  end
end

def load_isbns(url)
  status,content = read_url(url)  
  if status == :error
    raise content
  elsif status == :timeout
    raise 'timeout'
  end

  isbns = []
  content.scan(/(?:\d{3}-?)?\d{10}/).each {|match| isbns << match.delete('-') }

  return isbns
end

def write_file(file, content)
  File.open(file, "w") do |file|
    file.write content
  end
end

def matches(values, tests)
  values.each do |v|
    tests.each do |t|
      return t if v.downcase.include?(t)
    end
  end
  nil
end

class Item
  attr_accessor :title, :author, :url, :subjects, :rating, :total_ratings, :review

  def <=>(other)
    c = compare(other.rating, rating)
    c = compare(other.total_ratings, total_ratings) if c == 0
    return c
  end

  def compare(n1, n2)
    if n1.nil? && n2.nil?
      return 0
    elsif n1.nil?
      return -1
    elsif n2.nil?
      return 1
    else
      return n1 <=> n2
    end
  end
end

url = ARGV[0] 

if !url
  raise 'Usage: isbn-lookup <url>'
end

isbns = load_isbns(url)
items = []

Ecs.options = { :aWS_access_key_id => '1P81NT7QS95C540F79G2' }
count = 0
pct = 0
isbns.each do |isbn|
  count += 1
  temp = (count*100) / isbns.size
  if temp >= (pct+5)
    pct = temp
    puts "#{pct}%"
  end
  res = Ecs.item_lookup(isbn, :search_index => 'Books', 
                              :id_type => 'ISBN',
                              :response_group => 'Small,Subjects,Reviews,EditorialReview')
  if res.has_error?
    puts res.error
  else
    xml_item = res.items[0]

    title = xml_item.get('itemattributes/title')

    subjs = xml_item.get_array('subject')
    subjects = nil
    if subjs 
      match = matches(subjs, $exclude) 
      if match && !matches(subjs, $include) 
        puts "Excluding #{title} because it matches exclude keyword #{match}"
        next
      end
      subjects = subjs.join(", ")
    end

    rating = xml_item.get('customerreviews/averagerating')
    next if rating && rating.to_f < $min_rating

    item = Item.new
    item.title = title
    item.author = xml_item.get('itemattributes/author')
    item.url = xml_item.get('detailpageurl')
    item.subjects = subjects
    item.rating = rating
    item.total_ratings = xml_item.get('customerreviews/totalreviews')

    reviews = xml_item/'editorialreview'
    if reviews
      item.review = Element.get_unescaped(reviews[0], 'content')
    end

    items << item
  end
end

if !items.empty?
  items.sort! 
  html = ERB.new(read_file('html.erb')).result(binding)
  write_file('./books.html', html)
  exec('./firefox', './books.html')
else
  puts 'no results'
end
